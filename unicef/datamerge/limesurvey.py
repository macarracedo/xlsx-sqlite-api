import urllib2
import json
import sys
# There is an generic json-rpc implemantation in Python but it dose not work for me in this case so I worte Some functions 

API_URL = 'https://unicef.ccii.es/index.php/admin/remotecontrol'
        
def get_session_key():
    req = urllib2.Request(url=API_URL,\
                          data='{\"method\":\"get_session_key\",\"params\":[\"admin\",\"mypassword\"],\"id\":1}')
    req.add_header('content-type', 'application/json')
    req.add_header('connection', 'Keep-Alive')
    try:
        f = urllib2.urlopen(req)
        myretun = f.read()
        #print myretun
        j=json.loads(myretun)
        return j['result']
    except :
        e = sys.exc_info()[0]
        print ( "<p>Error: %s</p>" % e )
		
def get_question_properties(skey,QuestionID):
    req = urllib2.Request(url=API_URL,\
                          data='{\"method\":\"get_question_properties\",\"params\":[\"'+skey+'\",'+QuestionID
                                    +',[\"gid\",\"type\",\"help\",\"language\",\"sid\",\"question_order\",\"question\",\"subquestions\"]],\"id\": 1}')

    req.add_header('content-type', 'application/json')
    req.add_header('connection', 'Keep-Alive')
    try:
        f = urllib2.urlopen(req)
        myretun = f.read()
        #print myretun
        j=json.loads(myretun)
        return j['result']
    except :
        e = sys.exc_info()[0]
        print ( "<p>Error: %s</p>" % e )

		
def release_session_key(relkey):
    req = urllib2.Request(url=API_URL,\
                          data='{\"method\":\"release_session_key\",\"params\":[\"'+relkey+'\"],\"id\":1}')
    req.add_header('content-type', 'application/json')
    req.add_header('connection', 'Keep-Alive')
    try:
        f = urllib2.urlopen(req)
        myretun = f.read()
        #print myretun
        j=json.loads(myretun)
        return j['result']
    except :
        e = sys.exc_info()[0]
        print ( "<p>Error: %s</p>" % e )


def export_responses2(skey,sid):
    req = urllib2.Request(url=API_URL,\
                          data='{\"method\":\"export_responses\",\"params\":[\"'+skey+'\",\"'+sid+'\",\"csv\",\"de\",\"full\"],\
"id\": 1}')
    req.add_header('content-type', 'application/json')
    req.add_header('connection', 'Keep-Alive')
    try:
        f = urllib2.urlopen(req)
        myretun = f.read()
        #print myretun
        j=json.loads(myretun)
        return j['result']
    except :
        e = sys.exc_info()[0]
        print ( "<p>Error: %s</p>" % e )	