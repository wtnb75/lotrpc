package main

import (
	"encoding/json"
	"flag"
	"log"
	"net"
	"net/http"
	"net/rpc"
)

type Greet int

func (g Greet) Hello(arg map[string]string, reply *map[string]string) error {
	if name, ok := arg["name"]; ok {
		(*reply)["hello"] = name
		(*reply)["result"] = "OK"
	} else {
		(*reply)["result"] = "NG"
	}
	log.Println("reply", reply)
	return nil
}

func main() {
	mode := flag.String("mode", "server", "server or client")
	hostport := flag.String("host", "localhost:9999", "TCP host:port")
	usehttp := flag.Bool("http", false, "http or raw tcp")
	method := flag.String("method", "Greet.Hello", "method name")
	params := flag.String("params", "{\"name\":\"world\"}", "parameter json")
	flag.Parse()
	if *mode == "server" {
		log.Println("server", *hostport, "http", *usehttp)
		rpc.Register(new(Greet))
		if *usehttp {
			rpc.HandleHTTP()
		}
		if listener, e := net.Listen("tcp", *hostport); e != nil {
			log.Fatalln("listen error", e)
		} else {
			if *usehttp {
				err := http.Serve(listener, nil)
				log.Fatalln("server error(http)", err)
			} else {
				rpc.Accept(listener)
				log.Println("finished")
			}
		}
	} else if *mode == "client" {
		log.Println("client", *hostport, "http", *usehttp)
		var client *rpc.Client
		var e error
		if *usehttp {
			client, e = rpc.DialHTTP("tcp", *hostport)
		} else {
			client, e = rpc.Dial("tcp", *hostport)
		}
		if e != nil {
			log.Fatalln("connect error", e)
		} else {
			reply := map[string]string{}
			paramdict := map[string]string{}
			if err := json.Unmarshal([]byte(*params), &paramdict); err != nil {
				log.Fatalln("json decode", err)
			}
			log.Println("method", *method, "args", paramdict)
			if err := client.Call(*method, paramdict, &reply); err != nil {
				log.Fatalln("call error", err)
			} else {
				log.Println("response", reply)
			}
		}
	}
}
