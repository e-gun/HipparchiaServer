package main

// https://tutorialedge.net/golang/go-redis-tutorial/
// https://golangdocs.com/golang-postgresql-example
// https://gobyexample.com/waitgroups
// https://www.ardanlabs.com/blog/2020/07/extending-python-with-go.html
// https://hackernoon.com/extending-python-3-in-go-78f3a69552ac

import (
	"C"
	"database/sql"
	"encoding/json"
	"fmt"
	"github.com/go-redis/redis"
	_ "github.com/lib/pq"
	"runtime"
	"sync"
)

const (
	rp			= `{"Addr": "localhost:6379", "Password": "", "DB": 0}`
	psq			= `{"Host": "localhost", "Port": 5432, "User": "hippa_rd", "Pass": "", "DBName": "hipparchiaDB"}`
	host		= "localhost"
	port		= 5432
	user		= "hippa_rd"
	password	= ""
	dbname		= "hipparchiaDB"
	// hitcap		= 200
	// threadcount	= 5
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
	k := "queries"
	c := int64(200)
	t := 5
	r := []byte(rp)
	p := []byte(psq)
	o := SharedLibrarySearcher(k, c, t, r, p)
	fmt.Println("results sent to redis as", o)
}

func SharedLibrarySearcher(searchkey string, hitcap int64, threadcount int, redislogininfo []byte, psqllogininfo []byte) string {
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
	fmt.Println("grabber", clientnumber)

	redisclient := redis.NewClient(&redis.Options{Addr: r.Addr, Password: r.Password, DB: r.DB})
	_, err := redisclient.Ping().Result()
	defer redisclient.Close()
	CheckError(err)
	fmt.Println("Connected to redis")

	psqlconn := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable", host, port, user, password, dbname)
	psqlcursor, err := sql.Open("postgres", psqlconn)
	CheckError(err)

	defer psqlcursor.Close()
	err = psqlcursor.Ping()
	CheckError(err)
	fmt.Println(fmt.Sprintf("%d Connected to %s on PostgreSQL", clientnumber, dbname))

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
				fmt.Println(fmt.Sprintf("grabber #%d added a result", clientnumber))
			}
		}
	}
}


func CheckError(err error) {
	if err != nil {
		panic(err)
	}
}
