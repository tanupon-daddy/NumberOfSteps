from flask import Flask, request, abort, render_template,make_response
import psycopg2
from pytz import timezone
import os
import sys
import json

BAR_COLOR = [['#7dccfe','#1e98ff'],['#8bd5b2', '#0acf70'],['#bb8edd', '#9941db']]
DAYofWEEK = [['日','#ff0000'],['月','#000000'],['火','#000000'],['水','#000000'],['木','#000000'],['金','#000000'],['土','#0000ff']]
REP_CANVAS = {
        "payload": {
            "google": {
                    "expectUserResponse": True,
                    "richResponse": {
                    "items": [
                        {
                        "htmlResponse": {
                            "url": "https://fierce-basin-12021.herokuapp.com/"
                            }
                        },
                        {
                        "simpleResponse": {
                            "textToSpeech": "昨日歩いた歩数です"
                        }
                        }
                    ]
                    }
                }
            }
        }

#POSTGRES_DSN = "postgres://qmdnglidmyuskv:2a5b826c6b5b2180250ac2a0cad17d2f35f03fa2b503a137ffa444fc797bc877@ec2-18-214-195-34.compute-1.amazonaws.com:5432/d1hupjvao7s8is"
POSTGRES_DSN= os.environ["POSTGRES_DSN"]

app = Flask(__name__)

def dbgprint(message):
    args = sys.argv
    if 2 <= len(args):
        if args[1]=='1':
            print(message)

def get_canvasJson(view=0):
    res = REP_CANVAS
    
    if view ==1:
        res.get("payload").get("google").get("richResponse").get("items")[0].get("htmlResponse")["url"]= "https://fierce-basin-12021.herokuapp.com/?view=1"
        res.get("payload").get("google").get("richResponse").get("items")[1].get("simpleResponse")["textToSpeech"]="昨日までの一週間で歩いた歩数です"
    else:
        res.get("payload").get("google").get("richResponse").get("items")[0].get("htmlResponse")["url"]= "https://fierce-basin-12021.herokuapp.com/?view=0"
        res.get("payload").get("google").get("richResponse").get("items")[1].get("simpleResponse")["textToSpeech"]="昨日歩いた歩数です"     


    dbgprint(res)
    return make_response(json.dumps(res))

def get_connection():
    return psycopg2.connect(POSTGRES_DSN)

def get_results(sql):
    dbgprint(sql)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            results = cur.fetchall()
            dbgprint(results)
        return results

def get_yesterdaymaxstep():
    sql = 'select trunc(max(step_count),-2) + 100  as max_step from v_before7day where date = (select max(date) as max_day from v_before7day)'
    results = get_results(sql)
    return results[0][0]

def get_weeklymaxstep():
    sql = 'select trunc(max(step_count),-2) + 100 as max_step from v_before7day'
    results = get_results(sql)
    return results[0][0]

def get_avgsteps(maxstep):
    sql = 'select user_name ,round(avg(step_count)) as avg_step,round(COALESCE(avg(step_count) * 90 / NULLIF(%s,0) ,0)) height,display_name  from v_before7day group by user_name,display_name order by user_name ' % maxstep
    results = get_results(sql)
    return results

def get_weeklysteps(maxstep):
    sql = 'select user_name , to_char(date,\'mmdd\') as day1, to_char(date,\'mm/dd\') as day2 , step_count ,round(COALESCE(step_count * 90 / NULLIF(%s,0) ,0)) height, cast(EXTRACT(DOW from date) as integer) as dow,display_name   from v_before7day order by date,user_name' % maxstep
    results = get_results(sql)
    return results

def get_weekdays():
    sql = 'select to_char(date,\'mmdd\') as day1, to_char(date,\'mm/dd\') as day2 , cast(EXTRACT(DOW from date) as integer) as dow from v_before7day group by date order by date'
    results = get_results(sql)
    return results

def get_yesterdaysteps(maxstep):
    sql = 'select user_name , to_char(date,\'mm/dd\') as day , step_count ,COALESCE(step_count * 90 / NULLIF(%s,0) ,0)  height, cast(EXTRACT(DOW from date) as integer) as dow,display_name from v_before7day where date = (select max(date) as max_day from v_before7day) order by user_name' % maxstep
    results = get_results(sql)
    return results

@app.route('/hello', methods=['GET'])
def hello():
    name = "Hoge"
    #return name
    return render_template('hello.html', title='flask test', name=name) #変更

@app.route('/webhook', methods=['POST'])
def webhook():
    dbgprint(request)
    json_req = request.get_json()
    dbgprint(json_req)
    #json_data = json.loads(REP_CANVAS)
    #print(type(json_data))
    view = 0
    if json_req.get("queryResult").get("parameters").get("view") == "weekly":
        view =1
        dbgprint("週間")
    dbgprint(str(view))
    res = get_canvasJson(view)
    res.headers['Content-Type'] = 'application/json'
    return res

@app.route('/')
def index():
    #クエリストリングでviewが0なら前日表示、1なら週間表示、デフォルトは0
    view = request.args.get('view',0,int)
    dbgprint("view:" + str(view))
    #NestHubからのリクエストかどうか判定。nestが0ならnest以外、1ならnest、デフォルトは0
    nest = request.args.get('nest',0,int)
    dbgprint("nest:" + str(nest))

    yesterdaymaxstep = get_yesterdaymaxstep()
    weeklymaxstep = get_weeklymaxstep()
    avgsteps = get_avgsteps(str(weeklymaxstep))
    weekdays = get_weekdays()
    weeklysteps = get_weeklysteps(str(weeklymaxstep))
    yesterdaysteps = get_yesterdaysteps(str(yesterdaymaxstep))
    yesterday = [yesterdaysteps[0][1],yesterdaysteps[0][4]]
    dbgprint(yesterday)

#    return render_template('index.html', title='index test',yesterdaymaxstep=yesterdaymaxstep,weeklymaxstep=weeklymaxstep, avgsteps=avgsteps,weekdays=weekdays,weeklysteps=weeklysteps,yesterdaysteps=yesterdaysteps,yesterday=yesterday,bar_color=BAR_COLOR,DAYofWEEK=DAYofWEEK)
    if view == 1:
        return render_template('weekly.html', title='一週間の歩数推移',yesterdaymaxstep=yesterdaymaxstep,weeklymaxstep=weeklymaxstep, avgsteps=avgsteps,weekdays=weekdays,weeklysteps=weeklysteps,yesterdaysteps=yesterdaysteps,yesterday=yesterday,bar_color=BAR_COLOR,DAYofWEEK=DAYofWEEK)
    else:
        return render_template('yesterday.html', title='前日の歩数',yesterdaymaxstep=yesterdaymaxstep,weeklymaxstep=weeklymaxstep, avgsteps=avgsteps,weekdays=weekdays,weeklysteps=weeklysteps,yesterdaysteps=yesterdaysteps,yesterday=yesterday,bar_color=BAR_COLOR,DAYofWEEK=DAYofWEEK)

@app.route("/step", methods=["GET", "POST"])
def step():
    try:
        if request.method == "GET":
            return """
            <form action="/step" method="POST">
            <input name="stepdate"></input>
            <input name="stepcount"></input>
            <input type="submit" value="送信する">
            </form>"""
        else:
            stepdate = str(request.form["stepdate"])
            stepcount = str(request.form["stepcount"])
            username = str(request.form["username"])
            msg = "username : " + username + ",stepdate : " + stepdate + ",stepcount : " + stepcount
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('INSERT INTO step_hist_row(user_name, step_date,step_count) VALUES ((%s), (%s), (%s));', (username,stepdate,stepcount,))
                conn.commit()
            return msg + ',OK'
    except psycopg2.Error as e:
        errmsg = msg + ",PostgreSQL Error: " + e.diag.message_primary
        print(errmsg)

        return errmsg

@app.route('/health_check')
def health_check():
    return 'OK'

if __name__ == "__main__":
#    app.run()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)