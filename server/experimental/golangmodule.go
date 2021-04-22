package main

import (
	"C"
	"database/sql"
	"encoding/json"
	"flag"
	"fmt"
	"github.com/go-redis/redis"
	_ "github.com/lib/pq"
	"runtime"
	"sync"
)

/*

for python cli

import redis
import json
rc = redis.ConnectionPool(host='127.0.0.1', port=6379, db=0)
c = redis.Redis(connection_pool=rc)
l = {'TempTable': '', 'PsqlQuery': 'SELECT wkuniversalid, index, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words, annotations FROM lt0914 WHERE  ( stripped_line ~* $1 )  LIMIT 200', 'PsqlData': '(^|\\s)strage(\\s|$)'}
c.sadd('queries', json.dumps(l))

*/

// https://tutorialedge.net/golang/go-redis-tutorial/
// https://golangdocs.com/golang-postgresql-example
// https://gobyexample.com/waitgroups
// https://www.ardanlabs.com/blog/2020/07/extending-python-with-go.html
// https://hackernoon.com/extending-python-3-in-go-78f3a69552ac
// https://blog.filippo.io/building-python-modules-with-go-1-5/

// https://github.com/go-python/gopy
// pip install pybindgen


const (
	rp			= `{"Addr": "localhost:6379", "Password": "", "DB": 0}`
	psq			= `{"Host": "localhost", "Port": 5432, "User": "hippa_rd", "Pass": "", "DBName": "hipparchiaDB"}`
)

type PrerolledQuery struct {
	TempTable string
	PsqlQuery string
	PsqlData  string
}

type DbWorkline struct {
	WkUID		string
	TbIndex		int
	Lvl5Value	string
	Lvl4Value	string
	Lvl3Value	string
	Lvl2Value	string
	Lvl1Value	string
	Lvl0Value	string
	MarkedUp	string
	Accented	string
	Stripped	string
	Hypenated	string
	Annotations	string
}

type RedisLogin struct {
	Addr		string
	Password	string
	DB			int
}

type PostgresLogin struct {
	Host 		string
	Port		int
	User 		string
	Pass 		string
	DBName		string
}


func main() {
	fmt.Println("HipparchiaGolangModule Testing Ground")

	var k string
	var c int64
	var t int
	var r string
	var p string

	flag.StringVar(&k, "k", "queries", "redis key to use")
	flag.Int64Var(&c, "c", 200, "max hit count")
	flag.IntVar(&t, "t", 5, "number of goroutines to dispatch")
	flag.StringVar(&r, "r", rp, "redis logon information (as a JSON string)")
	flag.StringVar(&p, "p", psq, "psql logon information (as a JSON string)")
	flag.Parse()

	o := gosearch(k, c, t, []byte(r), []byte(p))
	fmt.Println("results sent to redis as", o)
}


//Execute a series of SQL queries stored in redis by dispatching a collection of goroutines
func gosearch(searchkey string, hitcap int64, threadcount int, redislogininfo []byte, psqllogininfo []byte) string {
	runtime.GOMAXPROCS(threadcount)

	r := decoderedislogin(redislogininfo)
	p := decodepsqllogin(psqllogininfo)

	var awaiting sync.WaitGroup

	for i:=0; i < threadcount; i++ {
		awaiting.Add(1)
		go grabber(i, hitcap, searchkey, r, p, &awaiting)
	}

	awaiting.Wait()

	resultkey := searchkey + "_results"
	return resultkey
}


func decoderedislogin(redislogininfo []byte) RedisLogin {
	var rl RedisLogin
	err := json.Unmarshal(redislogininfo, &rl)
	CheckError(err)
	return rl
}


func decodepsqllogin(psqllogininfo []byte) PostgresLogin {
	var ps PostgresLogin
	err := json.Unmarshal(psqllogininfo, &ps)
	CheckError(err)
	return ps
}


func grabber(clientnumber int, hitcap int64, searchkey string, r RedisLogin, p PostgresLogin, awaiting *sync.WaitGroup) {
	defer awaiting.Done()
	// fmt.Println("Hello from grabber", clientnumber)

	redisclient := redis.NewClient(&redis.Options{Addr: r.Addr, Password: r.Password, DB: r.DB})
	_, err := redisclient.Ping().Result()
	defer redisclient.Close()
	CheckError(err)
	// fmt.Println("Connected to redis")

	psqlconn := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
		p.Host, p.Port, p.User, p.Pass, p.DBName)
	psqlcursor, err := sql.Open("postgres", psqlconn)
	CheckError(err)

	defer psqlcursor.Close()
	err = psqlcursor.Ping()
	CheckError(err)
	// fmt.Println(fmt.Sprintf("grabber #%d Connected to %s on PostgreSQL", clientnumber, dbname))

	resultkey := searchkey + "_results"

	for {
		// [a] get a query
		byteArray, err := redisclient.SPop(searchkey).Result()
		if err != nil { break }
		fmt.Println(fmt.Sprintf("grabber #%d found work", clientnumber))

		// [b] decode it
		var prq PrerolledQuery
		err = json.Unmarshal([]byte(byteArray), &prq)
		CheckError(err)
		// fmt.Printf("%+v\n", prq)

		// [c] build a temp table if needed
		if prq.PsqlQuery != "" {
			_, err := psqlcursor.Query(prq.TempTable)
			CheckError(err)
		}

		// [d] execute the query
		foundrows, err := psqlcursor.Query(prq.PsqlQuery, prq.PsqlData)
		CheckError(err)

		// [e] iterate through the finds
		defer foundrows.Close()
		for foundrows.Next() {
			// [e1] convert the find to a DbWorkline
			var thehit DbWorkline
			err = foundrows.Scan(&thehit.WkUID, &thehit.TbIndex, &thehit.Lvl5Value, &thehit.Lvl4Value, &thehit.Lvl3Value,
				&thehit.Lvl2Value, &thehit.Lvl1Value, &thehit.Lvl0Value, &thehit.MarkedUp, &thehit.Accented,
				&thehit.Stripped, &thehit.Hypenated, &thehit.Annotations)
			CheckError(err)
			//fmt.Println(thehit)

			// [e2] if you have not hit the find cap, store the result in 'querykey_results'
			hitcount, err := redisclient.SCard(resultkey).Result()
			CheckError(err)
			if hitcount >= hitcap {
				// trigger the break in the outer loop
				redisclient.Del(searchkey)
			} else {
				jsonhit, err := json.Marshal(thehit)
				CheckError(err)
				redisclient.SAdd(resultkey, jsonhit)
				// fmt.Println(fmt.Sprintf("grabber #%d added a result to %s", clientnumber, resultkey))
			}
		}
	}
}


func CheckError(err error) {
	if err != nil {
		panic(err)
	}
}
