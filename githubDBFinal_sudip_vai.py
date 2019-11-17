#!/usr/bin/env python
# coding: utf-8

# In[7]:


import requests
from pprint import pprint
import os
import mysql.connector 
from datetime import datetime
API = "api"

BASE = "api"
PROJECT = 



mydb = mysql.connector.connect(
          host="localhost",
          user="root",
          passwd="1234",
          database="github_miner"
        )

def get(url, user = '',param = {},  password ='',header_accept='application/vnd.github.mercy-preview+json'):
    req=requests.get(url, auth=(user,password),
                    headers={'Accept':header_accept},
                     params = param
                    )
    return req
def get_row(url):
    response = requests.get(url, auth=(user,password))
    return response

def isLast(req):
    if 'next' in req.links.keys():
        return False
    return True

userList = []


# In[8]:


pageCounter=1
finished = False

inlineCommentedFile = []
reviewCommentList=[]

mycursor = mydb.cursor()
#mycursor.execute("DROP TABLE IF EXISTS review_comments")
#mycursor.execute("CREATE TABLE review_comments (id VARCHAR(100) PRIMARY KEY,body VARCHAR(5000),position INT , original_position INT, path VARCHAR(500),commit_id VARCHAR(50),user_id INT,pull_request_review_id INT,created_at DATETIME, is_a_reply VARCHAR(10), in_reply_to_id INT) ENGINE = MYISAM")
mycursor.close()
state = "open"
while not finished:
    print(state)
    reviewComment = get(BASE+"pulls/comments?page={}&per_page=100&state={}".format(pageCounter, state))
    pageCounter+=1
    if isLast(reviewComment):
        finished =True
    reviewCommentsJson = reviewComment.json()
    primary_keys = set()
    for rc in reviewCommentsJson:
        #print(str(rc['position']))
        #pprint(rc['diff_hunk'])
        #pprint(rc)
        reviewCommentDic = {}
        reviewCommentDic['id'] = PROJECT+"pulls/comments/"+str(rc['id'])
        
        #print(len(reviewCommentDic['id'])*8)
        reviewCommentDic['body'] = str(rc['body']).replace("'", "")
        #print(rc['body'])
        #reviewCommentDic['diff_hunk'] = rc['diff_hunk']
        reviewCommentDic['position'] = rc['position']
        if(rc['position'] is None):
            reviewCommentDic['position'] = "NULL"
        reviewCommentDic['original_position'] = rc['original_position']
        reviewCommentDic['path'] = rc['path']
        reviewCommentDic['commit_id'] = rc['commit_id']
        inlineCommentedFile.append(BASE+rc['path'])
        
        if bool(rc['user']):
            reviewCommentDic['user_id'] = rc['user']['id']
        else:
            reviewCommentDic['user_id'] = "NULL"
            
        reviewCommentDic['pull_request_review_id'] = str(rc['pull_request_review_id'])
        #reviewCommentDic['created_at'] = rc['created_at']
        reviewCommentDic['created_at'] = str(datetime.strptime(rc['created_at'], '%Y-%m-%dT%H:%M:%SZ'))
        #reviewCommentDic['updated_at'] = rc['updated_at']
        #reviewCommentDic['author_association'] = rc['author_association']
        #reviewCommentDic['path'] = rc['path']
        if 'in_reply_to_id' in rc.keys():
            reviewCommentDic['is_a_reply'] = str(True)
            reviewCommentDic['in_reply_to_id'] = rc['in_reply_to_id']
        else:
            reviewCommentDic['is_a_reply'] = str(False)
            reviewCommentDic['in_reply_to_id'] = "NULL"
        #print(reviewCommentDic)
        
        
        cursor = mydb.cursor()
        #cursor.execute("SELECT count(*) from review_comments where id={}".format(reviewCommentDic['id']))
        #print(cursor.fetchall())
        #cursor.close()
        #break
        
        sql = "INSERT INTO review_comments ( id, body, position, original_position, path, commit_id, user_id, pull_request_review_id, created_at, is_a_reply, in_reply_to_id ) VALUES ("        +"'"+reviewCommentDic['id']+"','"+reviewCommentDic['body']+"',"+"{}".format(reviewCommentDic['position'])+","+"{}".format(reviewCommentDic['original_position'])+",'"+reviewCommentDic['path']+"','"+reviewCommentDic['commit_id']+"','"+str(reviewCommentDic['user_id'])+"','"+str(reviewCommentDic['pull_request_review_id'])+"','"+reviewCommentDic['created_at']+"','"+str(reviewCommentDic['is_a_reply'])+"',"+"{}".format(reviewCommentDic['in_reply_to_id'])+") ON DUPLICATE KEY UPDATE in_reply_to_id={}".format(reviewCommentDic['in_reply_to_id'])
        #print(sql)
        '''
        sql = "INSERT INTO review_comments ( id, body, position, original_position, path, commit_id, user_id, pull_request_review_id, created_at, is_a_reply, in_reply_to_id ) VALUES ("\
        +"'"+reviewCommentDic['id']+"','"+reviewCommentDic['body']+"',"+"%s"+",'"+str(reviewCommentDic['original_position'])+"','"+reviewCommentDic['path']+"','"+reviewCommentDic['commit_id']+"','"+str(reviewCommentDic['user_id'])+"','"+str(reviewCommentDic['pull_request_review_id'])+"','"+reviewCommentDic['created_at']+"','"+str(reviewCommentDic['is_a_reply'])+"','"+str(reviewCommentDic['in_reply_to_id'])+"') ON DUPLICATE KEY UPDATE in_reply_to_id='{}'".format(reviewCommentDic['in_reply_to_id'])
        '''
        #print(sql)
        if(reviewCommentDic['id'] not in primary_keys):
            cursor.execute(sql)
            primary_keys.add(reviewCommentDic['id'])
        cursor.close()
        
        user = {}
        if(bool(rc['user'])):
            user['name'] = rc['user']['login']
            queryReq = get(API+'users/'+rc['user']['login'])
            if ('email' in queryReq.json().keys()) and (queryReq.json()['email']) is not None:
                user['email'] = str(queryReq.json()['email'])
                
            else:
                #pprint(rc)
                user['email'] = "NULL"
            user['id'] = rc['user']['id']
            if user not in userList:
                userList.append(user)
    if finished and state=='open':
        finished = False
        pageCounter=1
        state = 'closed'
        
print(userList)


# In[ ]:


# comments on a file for pull request there is pill request comments and pull request review comments
#for a pull or comment in that pul get all the relevent informations informations  like the previos block
commentList = []
pageCounter=1
finished = False
ct= 0

mycursor = mydb.cursor()
#mycursor.execute("DROP TABLE IF EXISTS comments")
#mycursor.execute("CREATE TABLE comments (id VARCHAR(100) PRIMARY KEY,body VARCHAR(500),created_at DATETIME,user_id INT) ENGINE = MYISAM")
mycursor.close()

primary_keys = set()

def parce_comment(comment):
    commentDict = {}
    commentDict['id'] = PROJECT+"comments/"+str(comment['id'])
    
    commentDict['body'] = comment['body']
    commentDict['created_at']=str(datetime.strptime(comment['created_at'], '%Y-%m-%dT%H:%M:%SZ'))
    #commentDict['created_at'] = comment['created_at']
    commentDict['user_id'] = comment['user']['id']
    #commentList.append(commentDict)
    
    cursor = mydb.cursor()
        
    sql = "INSERT INTO comments ( id, body, created_at, user_id) VALUES ("    +"'"+commentDict['id']+"','"+commentDict['body']+"','"+commentDict['created_at']+"','"+str(commentDict['user_id'])+"') ON DUPLICATE KEY UPDATE body='{}'".format(commentDict['body'])
    if commentDict['id'] not in primary_keys:
        cursor.execute(sql)
        primary_keys.add(commentDict['id'])
    cursor.close()
    #print(reviewCommentDic)
    return commentDict

while not finished:
    pullsJson = get(BASE+"pulls?page={}&per_page=100".format(pageCounter))
    pageCounter+=1
    #print("comes")
    if isLast(pullsJson):
        finished = True
    pullsJsonList = pullsJson.json()
    for pull in pullsJsonList:
        pageCounterInsize=1
        finishedInsize = False
        while not finishedInsize:
            commentsInPullRequest = get(pull['_links']['comments']['href']+"?page={}&per_page=100".format(pageCounterInsize))
            pageCounterInsize+=1
            if isLast(commentsInPullRequest):
                finishedInsize = True
            commentsInPull = commentsInPullRequest.json()
            for comment in commentsInPull:
                parce_comment(comment)
                user = {}
                if(bool(comment['user'])):
                    user['name'] = comment['user']['login']
                    #pprint(rc)
                    queryReq = get(API+'users/'+comment['user']['login'])
                    #print(queryReq.json().keys())
                    if ('email' in queryReq.json().keys()) and (queryReq.json()['email']) is not None:
                        user['email'] = str(queryReq.json()['email'])

                    else:
                        #pprint(rc)
                        user['email'] = "NULL"
                    user['id'] = comment['user']['id']
                    if user not in userList:
                        userList.append(user)
                
pageCounter=1
finished = False
ct= 0
while not finished:
    issuesJson = get(BASE+"issues?page={}&per_page=100".format(pageCounter))
    pageCounter+=1
    #print("comes")
    if isLast(issuesJson):
        finished = True
    issuesJsonList = issuesJson.json()
    
    for issue in issuesJsonList:
        pageCounterInsize=1
        finishedInsize = False
        while not finishedInsize:
            commentsInIssue = get(issue['comments_url']+"?page={}&per_page=100".format(pageCounterInsize))
            pageCounterInsize+=1
            if isLast(commentsInPullRequest):
                finishedInsize = True
            commentsInIssueList = commentsInIssue.json()
            for comment in commentsInIssueList:
                #pprint(comment)
                parce_comment(comment)
                user = {}
                if(bool(comment['user'])):
                    user['name'] = comment['user']['login']
                    #pprint(rc)
                    queryReq = get(API+'users/'+comment['user']['login'])
                    #print(queryReq.json().keys())
                    if ('email' in queryReq.json().keys()) and (queryReq.json()['email']) is not None:
                        user['email'] = str(queryReq.json()['email'])
                    else:
                        #pprint(rc)
                        user['email'] = "NULL"
                    user['id'] = comment['user']['id']
                    if user not in userList:
                        userList.append(user)
                
                
#print(len(commentList))
#print(commentList)
pprint(userList)
#collect author info from both of those lists


# In[ ]:


import os
import mysql.connector
from datetime import datetime


mycursor = mydb.cursor()
#mycursor.execute("DROP TABLE IF EXISTS commits")
#mycursor.execute("CREATE TABLE commits (id VARCHAR(50) PRIMARY KEY,author_name VARCHAR(100),author_email VARCHAR(100) ,date DATETIME, author_id INT,committer_name VARCHAR(100),committer_email VARCHAR(100),committer_id INT, message VARCHAR(500)) ENGINE = MYISAM")

#mycursor.execute("DROP TABLE IF EXISTS files")# commit id, branch, raw file location
#mycursor.execute("CREATE TABLE files (commit_id VARCHAR(50) ,project_name VARCHAR(100), branch_name VARCHAR(100), file_url  VARCHAR(500)) ENGINE = MYISAM")


mycursor.close()

primary_keys = set()

def parse_commit(ci):
    commitInfoDict = {}
    #pprint(ci)
    if (ci['committer'] is None) or (ci['author'] is None):
        return commitInfoDict
    
    commitInfoDict['commit_id'] = str(ci['sha'])
    commitInfoDict['author_name'] = ci['commit']['author']['name']
    commitInfoDict['author_email'] = ci['commit']['author']['email']
    commitInfoDict['date'] = str(datetime.strptime(ci['commit']['author']['date'], '%Y-%m-%dT%H:%M:%SZ'))
    #commitInfoDict['date'] = str(ci['commit']['author']['date'])
    
    if ci['author'] is not None:
        commitInfoDict['author_id'] = ci['author']['id']
    else:
        commitInfoDict['author_id'] = "NULL"
        print("author id null")
        
    commitInfoDict['committer_name'] = ci['commit']['committer']['name']
    commitInfoDict['committer_email'] = ci['commit']['committer']['email']

    if ci['committer'] is not None:
        commitInfoDict['committer_id'] = ci['committer']['id']
    else:
        commitInfoDict['committer_id'] = "NULL"
        
    commitInfoDict['message'] = str(ci['commit']['message']).replace("'", "")
    cursor = mydb.cursor()
        
    sql = "INSERT INTO commits (id,author_name,author_email,date, author_id,committer_name,committer_email,committer_id, message) VALUES ("+    "'"+commitInfoDict['commit_id']+"','"+commitInfoDict['author_name']+"','"+commitInfoDict['author_email']+"','"+commitInfoDict['date']+"',"+"{}".format(commitInfoDict['author_id'])+",'"+commitInfoDict['committer_name']+"','"+commitInfoDict['committer_email']+"',"+"{}".format(commitInfoDict['committer_id'])+",'"+commitInfoDict['message']+"') ON DUPLICATE KEY UPDATE message='{}'".format(commitInfoDict['message'])
    #print(sql)
    if commitInfoDict['commit_id'] not in primary_keys:
        cursor.execute(sql)
        primary_keys.add(commitInfoDict['commit_id'])
        if commitInfoDict['author_id'] == "NULL":
            print("author id null")
    cursor.close()
    return commitInfoDict

pageCounter=1
finished = False
branchList = []
while not finished:
    branch_qeq = get(BASE+"branches?page={}&per_page=100".format(pageCounter))
    pageCounter+=1
    if isLast(branch_qeq):
        finished =True
    branch_list = branch_qeq.json()
    for branch in branch_list:
        branchList.append(branch['name'])
all_commits_info = []
for branch in branchList:
    commit_count=0
    pageCounter=1
    finished = False
    branch_commits = []
    print(branch)
    while not finished:
        commitRequest = get(BASE+"commits?page={}&per_page=100".format(pageCounter), param = {"sha":branch})
        pageCounter+=1
        if isLast(commitRequest):
            finished =True
        commitInfoList = commitRequest.json()
        #pprint(commitInfoList)
        for ci in commitInfoList:
            commitInfoDict = {}
            commitInfoDict['author_name'] = ci['commit']['author']['name']
            commitInfoDict['author_email'] = ci['commit']['author']['email']
            commitInfoDict['date'] = ci['commit']['author']['date']
            if ci['author'] is None:
                commit_count+=1
                continue
            else:
                commitInfoDict['author_id'] = ci['author']['id']
            author = {}
            author['id'] = commitInfoDict['author_id'] 
            author['name'] = commitInfoDict['author_name'] 
            author['email'] = commitInfoDict['author_email'] 
            if author not in userList:
                userList.append(author)

            commitInfoDict['committer_name'] = ci['commit']['committer']['name']
            commitInfoDict['committer_email'] = ci['commit']['committer']['email']

            if ci['committer'] is None:
                commit_count+=1
                continue
            else:
                commitInfoDict['committer_id'] = ci['committer']['id']
            #author info
            author = {}
            author['id'] = commitInfoDict['committer_id'] 
            author['name'] = commitInfoDict['committer_name'] 
            author['email'] = commitInfoDict['committer_email'] 
            if author not in userList:
                userList.append(author)    
            commitInfoDict['message'] = ci['commit']['message']
            commitInfoDict['commit_id'] = ci['sha']
            commit_count+=1
            #print(commitInfoDict['message'])
            branch_commits.append(commitInfoDict['commit_id'])
    print(commit_count)
    for commit_hash in reversed(branch_commits):
        commitDict = parse_commit(get(BASE+'commits/'+commit_hash).json())
    
        file_list = get(BASE+'commits/'+commit_hash).json()['files']
        #pprint(file_list)
        for file in file_list:
            if BASE+file['filename'] in inlineCommentedFile:
                location = file['filename']
                raw_url = file['raw_url']
                status = file['status']
                response = requests.get(raw_url, auth=(user,password))
                
                cursor = mydb.cursor()
                #"id ,project_name, branch_name, file_url"
                sql = "INSERT INTO files (commit_id ,project_name, branch_name, file_url) VALUES ("+"'"+commit_hash+"',"+"'{}".format(PROJECT)+"','"+branch+"','"+raw_url+"')"
                #print(sql)
                cursor.execute(sql)
                cursor.close()
                '''
                if response.status_code == 200:
                    location = BASE+file['filename']
                    folder_location = location.replace('/','#')
                    folder_location = folder_location.replace(':','$')
                    final_location = os.path.join('file_contents', folder_location+"&"+branch)
                    #print(final_location)
                    
                    if not os.path.exists(final_location):
                        os.mkdir(final_location)
                    save_location = final_location+'/'+commit_hash
                    if os.path.exists(save_location):
                        print(commit_hash)
                    with open(save_location, 'wb') as f:
                        f.write(response.content)
                '''
    
pprint(userList)


# In[ ]:


pprint(get(API+"users/"+"m-imtiaz").json()['name'])
s = get(API+"users/"+"m-imtiaz").json()['name']
print(type(s))
print(len(s))
for ch in s:
    print(ch, end = '')


# In[ ]:


pprint(userList)


# In[ ]:


#pull request information merged or not 

pullInfo = []
pageCounter=1
finished = False
print("comes")
mycursor = mydb.cursor()
mycursor.execute("DROP TABLE IF EXISTS pulls")
mycursor.execute("CREATE TABLE pulls (id VARCHAR(100) PRIMARY KEY,commit_id VARCHAR(100), user_id INT, state VARCHAR(10), number INT,created_at DATETIME) ENGINE = MYISAM")
mycursor.close()

print("comes")
state = "open"
while not finished:
    pullsJson = get(BASE+"pulls?page={}&per_page=100&state={}".format(pageCounter,state))
    print(BASE+"pulls?page={}&per_page=100&state={}".format(pageCounter,state))
    pageCounter+=1
    #print("comes")
    if isLast(pullsJson):
        finished =True
    pullsJsonList = pullsJson.json()
    primary_keys = set()
    for pull in pullsJsonList:#[4:5]: #many pull request for one project
        pprint(len(get(pull['_links']['commits']['href']).json()))
        #break
        pull_dict = {}
        pull_dict['id'] = PROJECT+str(pull['id'])
        if bool(pull['user']):
            pull_dict['user_id'] = pull['user']['id']
        else:
            pull_dict['user_id'] = "NULL"
        pull_dict['commit_id'] = pull['base']['sha']
        pull_dict['state'] = pull['state']
        pull_dict['number'] = pull['number']
        pull_dict['title'] = pull['title']
        pull_dict['body'] = pull['body']
        pull_dict['created_at'] = str(datetime.strptime(pull['created_at'], '%Y-%m-%dT%H:%M:%SZ'))
        #pull_dict['closed_at'] = str(datetime.strptime(pull['closed_at'], '%Y-%m-%dT%H:%M:%SZ'))
        
        cursor = mydb.cursor()
        
        sql = "INSERT INTO pulls ( id,commit_id, user_id,state, number,created_at) VALUES ("+"'"+pull_dict['id']+"','"+pull_dict['commit_id']+"',"+"{}".format(pull_dict['user_id'])+",'"+pull_dict['state']+"','"+str(pull_dict['number'])+"','"+pull_dict['created_at']+"') ON DUPLICATE KEY UPDATE state='{}'".format(pull_dict['state'])
        print(sql)
        if pull_dict['id'] not in primary_keys:
            cursor.execute(sql)
            primary_keys.add(pull_dict['id'])
        cursor.close()
        #pull_dict['closed_at'] = pull['closed_at']
        #pull_dict['created_at'] = pull['created_at']
        
        #pull_dict['title'] = pull['title']
        #pprint(pull_dict)
        user = {}
        if(bool(pull['user'])):
            user['name'] = pull['user']['login']
            #pprint(rc)
            queryReq = get(API+'users/'+user['name'])
            #print(queryReq.json().keys())
            if ('email' in queryReq.json().keys()) and (queryReq.json()['email']) is not None:
                user['email'] = str(queryReq.json()['email'])

            else:
                #pprint(rc)
                user['email'] = "NULL"
            user['id'] = pull['user']['id']
            if user not in userList:
                userList.append(user)
        
        if finished and state=='open':
            finished = False
            pageCounter=1
            state = 'closed'
pprint(userList)


# In[ ]:


#pull request information merged or not 

pullInfo = []
pageCounter=1
finished = False
print("comes")
mycursor = mydb.cursor()
mycursor.execute("DROP TABLE IF EXISTS pulls")
mycursor.execute("CREATE TABLE pulls (id VARCHAR(100) PRIMARY KEY,commit_id VARCHAR(100), user_id INT, state VARCHAR(10), number INT,title VARCHAR(150), body VARCHAR(500),created_at DATETIME) ENGINE = MYISAM")
mycursor.close()

print("comes")
state = "open"
while not finished:
    pullsJson = get(BASE+"pulls?page={}&per_page=100&state={}".format(pageCounter,state))
    print(BASE+"pulls?page={}&per_page=100&state={}".format(pageCounter,state))
    pageCounter+=1
    #print("comes")
    if isLast(pullsJson):
        finished =True
    pullsJsonList = pullsJson.json()
    primary_keys = set()
    for pull in pullsJsonList:#[4:5]: #many pull request for one project
        pprint(len(get(pull['_links']['commits']['href']).json()))
        #break
        
        
        if finished and state=='open':
            finished = False
            pageCounter=1
            state = 'closed'
pprint(userList)


# In[ ]:


#user saving
mycursor = mydb.cursor()
mycursor.execute("DROP TABLE IF EXISTS users")
mycursor.execute("CREATE TABLE users (id INT PRIMARY KEY,name VARCHAR(100), email VARCHAR(50)) ENGINE = MYISAM")
mycursor.close()
primary_keys = set()
for user in userList:
    cursor = mydb.cursor()
    
    sql = "INSERT INTO users ( id, name, email) VALUES ("+"'"+str(user['id'])+"','"+user['name']+"','"+user['email']+"') ON DUPLICATE KEY UPDATE email='{}'".format(user['email'])
    #sql = "INSERT INTO users ( id, name, email) VALUES ("+"'"+str(user['id'])+"','"+user['name']+"','"+user['email']+"')"
    print(sql)
    if user['id'] not in primary_keys:
        cursor.execute(sql)
        primary_keys.add(user['id'])
    cursor.close()


# In[ ]:



branch_qeq = get(BASE+"branches")
branch_list = branch_qeq.json()
for branch in branch_list:
    pprint(len(get(BASE+"pulls/comments",param = {"sha":branch['name']}).json()))
    
 


# In[ ]:





# In[ ]:





# In[ ]:




