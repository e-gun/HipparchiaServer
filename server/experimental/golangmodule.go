package hipparchiagolangsearching
// package main

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
	var g int
	var r string
	var p string

	flag.StringVar(&k, "k", "queries", "redis key to use")
	flag.Int64Var(&c, "c", 200, "max hit count")
	flag.IntVar(&g, "t", 5, "number of goroutines to dispatch")
	flag.StringVar(&r, "r", rp, "redis logon information (as a JSON string)")
	flag.StringVar(&p, "p", psq, "psql logon information (as a JSON string)")
	flag.Parse()

	rl := decoderedislogin([]byte(r))
	po := decodepsqllogin([]byte(p))

	o := HipparchiaGolangSearcher(k, c, g, rl, po)
	fmt.Println("results sent to redis as", o)
}

//Generate new redis credentials
func NewRedisLogin(ad string, pw string, db int) *RedisLogin {
	return &RedisLogin{
		Addr: ad,
		Password: pw,
		DB: db,
	}
}


//Generate new postgres credentials
func NewPostgresLogin(ho string, po int, us string, pw string, db string) *PostgresLogin {
	return &PostgresLogin{
		Host: ho,
		Port: po,
		User: us,
		Pass: pw,
		DBName: db,
	}
}

//Execute a series of SQL queries stored in redis by dispatching a collection of goroutines
func HipparchiaGolangSearcher(searchkey string, hitcap int64, goroutines int, r RedisLogin, p PostgresLogin) string {
	runtime.GOMAXPROCS(goroutines)

	var awaiting sync.WaitGroup

	for i:=0; i < goroutines; i++ {
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
	checkerror(err)
	return rl
}


func decodepsqllogin(psqllogininfo []byte) PostgresLogin {
	var ps PostgresLogin
	err := json.Unmarshal(psqllogininfo, &ps)
	checkerror(err)
	return ps
}


func grabber(clientnumber int, hitcap int64, searchkey string, r RedisLogin, p PostgresLogin, awaiting *sync.WaitGroup) {
	defer awaiting.Done()
	// fmt.Println("Hello from grabber", clientnumber)

	redisclient := redis.NewClient(&redis.Options{Addr: r.Addr, Password: r.Password, DB: r.DB})
	_, err := redisclient.Ping().Result()
	defer redisclient.Close()
	checkerror(err)
	// fmt.Println("Connected to redis")

	psqlconn := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
		p.Host, p.Port, p.User, p.Pass, p.DBName)
	psqlcursor, err := sql.Open("postgres", psqlconn)
	checkerror(err)

	defer psqlcursor.Close()
	err = psqlcursor.Ping()
	checkerror(err)
	// fmt.Println(fmt.Sprintf("grabber #%d Connected to %s on PostgreSQL", clientnumber, dbname))

	resultkey := searchkey + "_results"

	for {
		// [a] get a query
		byteArray, err := redisclient.SPop(searchkey).Result()
		if err != nil { break }
		// fmt.Println(fmt.Sprintf("grabber #%d found work", clientnumber))

		// [b] decode it
		var prq PrerolledQuery
		err = json.Unmarshal([]byte(byteArray), &prq)
		checkerror(err)
		// fmt.Printf("%+v\n", prq)

		// [c] build a temp table if needed
		if prq.PsqlQuery != "" {
			_, err := psqlcursor.Query(prq.TempTable)
			checkerror(err)
		}

		// [d] execute the query
		foundrows, err := psqlcursor.Query(prq.PsqlQuery, prq.PsqlData)
		checkerror(err)

		// [e] iterate through the finds
		defer foundrows.Close()
		for foundrows.Next() {
			// [e1] convert the find to a DbWorkline
			var thehit DbWorkline
			err = foundrows.Scan(&thehit.WkUID, &thehit.TbIndex, &thehit.Lvl5Value, &thehit.Lvl4Value, &thehit.Lvl3Value,
				&thehit.Lvl2Value, &thehit.Lvl1Value, &thehit.Lvl0Value, &thehit.MarkedUp, &thehit.Accented,
				&thehit.Stripped, &thehit.Hypenated, &thehit.Annotations)
			checkerror(err)
			//fmt.Println(thehit)

			// [e2] if you have not hit the cap on finds, store the result in 'querykey_results'
			hitcount, err := redisclient.SCard(resultkey).Result()
			checkerror(err)
			if hitcount >= hitcap {
				// trigger the break in the outer loop
				redisclient.Del(searchkey)
			} else {
				jsonhit, err := json.Marshal(thehit)
				checkerror(err)
				redisclient.SAdd(resultkey, jsonhit)
				// fmt.Println(fmt.Sprintf("grabber #%d added a result to %s", clientnumber, resultkey))
			}
		}
	}
}


func checkerror(err error) {
	if err != nil {
		panic(err)
	}
}


// note: we need a connection pool...
// panic: pq: remaining connection slots are reserved for non-replication superuser connections

