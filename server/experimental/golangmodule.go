package main

// https://tutorialedge.net/golang/go-redis-tutorial/
// https://golangdocs.com/golang-postgresql-example

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"github.com/go-redis/redis"
	_ "github.com/lib/pq"
)

const (
	host     = "localhost"
	port     = 5432
	user     = "hippa_rd"
	password = ""
	dbname   = "hipparchiaDB"
	hitcap	 = 200
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


func main() {
	fmt.Println("HipparchiaGolangModule Testing Ground")

	redisclient := redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
		Password: "",
		DB: 0,
	})

	_, err := redisclient.Ping().Result()
	CheckError(err)
	// fmt.Println("Connected to redis")

	psqlconn := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable", host, port, user, password, dbname)
	psqlcursor, err := sql.Open("postgres", psqlconn)
	CheckError(err)

	defer psqlcursor.Close()
	err = psqlcursor.Ping()
	CheckError(err)
	// fmt.Println(fmt.Sprintf("Connected to %s on PostgreSQL", dbname))

	searchkey := "queries"
	resultkey := searchkey + "_results"

	for {
		// [a] get a query
		byteArray, err := redisclient.SPop(searchkey).Result()
		if err != nil { break }
		// fmt.Println(byteArray)

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
			}
		}
	}
}


func CheckError(err error) {
	if err != nil {
		panic(err)
	}
}
