#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import requests
from pprint import pprint
import os
import mysql.connector
from datetime import datetime
import os
import time



user_auth = ''
password =''



'''
this get function simulates pythons request.get function with github authentication and header integrated to reuse again and again
'''
def get(url,param = {},header_accept='application/vnd.github.mercy-preview+json'):
    #print(user_auth, password)
    #print(url)
    while True:
        try:
            req=requests.get(url, auth=(user_auth,password),
                            headers={'Accept':header_accept},
                             params = param
                            )
            #print(user, password)
            #print(req.text)
            return req
        except:
            print("sleeping 30 secs error while processing ", url)
            time.sleep(30)
            continue
'''
same as the get function but for getting the raw files with different header
'''
def get_raw(url):
    #response = requests.get(url, auth=(user,password))
    while True:
        try:
            response = requests.get(url, auth=(user_auth,password),
                                    headers={'Accept':'application/vnd.github.v3.raw'}
                                   )
            return response
        except:
            print("raw sleeping 30 secs error while processing ", url)
            time.sleep(30)
            continue
'''
github api gives atmost 100 length json array as output so to get all this function checks if this is the last api output chunk or not
'''
def isLast(req):
    if 'next' in req.links.keys():
        return False
    return True

userList = []

'''
mine function gets as input the PROJECT = username+repo_name, BASE = APIlink+PROJECT and mines all the data in this repo
this function is called by the main function that gives it all the projects names of srbd and this function mines those projects
'''
def mine(BASE, PROJECT, mydb, API):

    print("BASE = ", BASE)
    print("project = ", PROJECT)
    
    ######### review_comments mining section starts#################
    pageCounter=1
    finished = False
    inlineCommentedFile = []
    reviewCommentList=[]
    userList = []
    
    state = "open"
    primary_keys = set()
    cursor = mydb.cursor()
    sql = "select id from review_comments where project_name ='"+PROJECT+"'"
    cursor.execute(sql)
    lst = cursor.fetchall()
    primary_keys = set(val[0] for val in lst)
    #print(primary_keys)
    cursor.close()
    '''
    as the github api doesn't get more than 100 json elements of a json array in any query this while loop is used with the 
    function isLast explained above to get all the elements of the json array requested by any api  
    '''
    while not finished:
        #print(state)
        reviewComment = get(BASE+"pulls/comments?page={}&per_page=100&state={}".format(pageCounter, state))
        pageCounter+=1
        if isLast(reviewComment):
            finished =True
        reviewCommentsJson = reviewComment.json()
        
        for rc in reviewCommentsJson:
            try:
                if(rc['id'] in primary_keys): #"pulls/comments/"+
                    continue
                reviewCommentDic = {}
                reviewCommentDic['project_name'] = PROJECT
                reviewCommentDic['id'] = rc['id']
                #print(len(reviewCommentDic['id'])*8)
                reviewCommentDic['body'] = str(rc['body']).replace("'", "")
                reviewCommentDic['body'] = reviewCommentDic['body'].replace("\\", "")
                reviewCommentDic['body'] = reviewCommentDic['body'].replace('"', '')
                #print(rc['body'])
                #reviewCommentDic['diff_hunk'] = rc['diff_hunk']
                reviewCommentDic['position'] = rc['position']
                reviewCommentDic['pull_no'] = rc['pull_request_url'].split('/')[-1]
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
                cursor = mydb.cursor()
                sql = "INSERT INTO review_comments ( project_name, id, pull_no, body, position, original_position, path, commit_id, user_id, pull_request_review_id, created_at, is_a_reply, in_reply_to_id ) VALUES ("                +"'"+reviewCommentDic['project_name']+"',"+"{}".format(reviewCommentDic['id'])+",'"+reviewCommentDic['pull_no']+"','"+reviewCommentDic['body']+"',"+"{}".format(reviewCommentDic['position'])+","+"{}".format(reviewCommentDic['original_position'])+",'"+reviewCommentDic['path']+"','"+reviewCommentDic['commit_id']+"','"+str(reviewCommentDic['user_id'])+"','"+str(reviewCommentDic['pull_request_review_id'])+"','"+reviewCommentDic['created_at']+"','"+str(reviewCommentDic['is_a_reply'])+"',"+"{}".format(reviewCommentDic['in_reply_to_id'])+") ON DUPLICATE KEY UPDATE in_reply_to_id={}".format(reviewCommentDic['in_reply_to_id'])
                cursor.execute(sql)
                primary_keys.add(reviewCommentDic['id'])
                cursor.close()

                user = {}
                '''
                for all these requests we are accumulating the users if there is a new user and adding that to our array
                '''
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
            except Exception as e:
                print("$$$ CATCH ERROR "+ e)
                print(PROJECT , "line no 170")
                continue
        '''
        by default pull api gives the closed pulls information to get the open pulls we need to change the state in the api link 
        '''
        if finished and state=='open':
            finished = False
            pageCounter=1
            state = 'closed'
    ######### review_comments mining section ends#################
    
    
    '''
    this and similar primary_keys is to collect and store only the unencountered elementts and not to waste time on the already 
    stored data and to continue from where it left off if stopped for any reason 
    '''
    primary_keys = set()
    cursor = mydb.cursor()
    sql = "select id from commits"
    cursor.execute(sql)
    lst = cursor.fetchall()
    primary_keys = set(val[0] for val in lst)
    #print(primary_keys)
    cursor.close()
    
    # parse_commit , given a json file of commit informstion this function extracts from it the important features and inserts into commits table #### 
    def parse_commit(ci,pull_no, commit_no,is_last_commit):
        commitInfoDict = {}
        #pprint(ci)
        commitInfoDict['commit_id'] = str(ci['sha'])
        commitInfoDict['author_name'] = ci['commit']['author']['name']
        commitInfoDict['author_email'] = ci['commit']['author']['email']
        commitInfoDict['date'] = str(datetime.strptime(ci['commit']['author']['date'], '%Y-%m-%dT%H:%M:%SZ'))
        #commitInfoDict['date'] = str(ci['commit']['author']['date'])
        if bool(ci['author']) and ci['author'] is not None:
            commitInfoDict['author_id'] = ci['author']['id']
        else:
            commitInfoDict['author_id'] = "NULL"
        commitInfoDict['committer_name'] = ci['commit']['committer']['name']
        commitInfoDict['committer_email'] = ci['commit']['committer']['email']
        if bool(ci['committer']) and ci['committer'] is not None:
            commitInfoDict['committer_id'] = ci['committer']['id']
        else:
            commitInfoDict['committer_id'] = "NULL"
        commitInfoDict['message'] = str(ci['commit']['message']).replace("'", "")
        commitInfoDict['message'] = commitInfoDict['message'].replace('"', '')
        commitInfoDict['message'] = commitInfoDict['message'].replace('\\', '')
        
        if len(commitInfoDict['message'])>5000:
            commitInfoDict['message'] = commitInfoDict['message'][:5000]
        #print("comes")
        if commitInfoDict['commit_id'] not in primary_keys:
            cursor = mydb.cursor()
            sql = "INSERT INTO commits (id,author_name,author_email,date, author_id,committer_name,committer_email,committer_id, message, pull_no, commit_no,is_last_commit, project_name) VALUES ("+            "'"+commitInfoDict['commit_id']+"','"+commitInfoDict['author_name']+"','"+commitInfoDict['author_email']+"','"+commitInfoDict['date']+"',"+"{}".format(commitInfoDict['author_id'])+",'"+commitInfoDict['committer_name']+"','"+commitInfoDict['committer_email']+"',"+"{}".format(commitInfoDict['committer_id'])+",'"+commitInfoDict['message']+"'"+",{}".format(pull_no)+",{},".format(commit_no)+"'{}'".format(str(is_last_commit)) +",'{}'".format(PROJECT)+ ") ON DUPLICATE KEY UPDATE message='{}'".format(commitInfoDict['message'])
            #print(sql)
            cursor.execute(sql)
            primary_keys.add(commitInfoDict['commit_id'])
            cursor.close()
        return commitInfoDict

    ############### change trigger calculation in review_comment table starts ########
    import subprocess
    jar_path = "change_calculation.jar"
    '''
    change_calculation funtion and change_calculatoin.jar is needed to calculate an important feature named change trigger
    this function get as input two file contents as two string str1, and str2 a line number to check if there is any change 
    in range of "max_change_range" above and below with respect to str1 and str2. 
    for memory limitation we just kept 80 line above and below our area of interest(AKA line number AKA review comment location)
    this functions output is used to update the comlumns of review_comment table
    '''
    def change_calculation(str1, str2, line_number, max_change_range=5):
        offset = 60
        if(line_number>offset):
            str1 = str1.split('\n')
            str2 = str2.split('\n')
            str1 = str1[line_number-offset:]
            str2 = str2[line_number-offset:]
            line_number = offset
            str1 = "\n".join(str1)
            str2 = "\n".join(str2)

        str1 = str1.split('\n')
        str2 = str2.split('\n')
        
        if len(str1)> line_number+offset:
            str1 = str1[:line_number+offset]
        if len(str2)> line_number+offset:
            str2 = str2[:line_number+offset]
        str1 = "\n".join(str1)
        str2 = "\n".join(str2)
        line_number = str(line_number)
        max_change_range = str(max_change_range)
        
        print("{},  {}, {}, {}".format(len(str1.split('\n')),len(str2.split('\n')),line_number,max_change_range))
        
        try:
            line_change = subprocess.check_output(['java', '-jar', jar_path]+ [str1, str2, line_number, max_change_range] )
        except Exception as e:
            line_change = 9999
            print("file long error")
            print(e)
        line_change = int(line_change)
        return line_change
    
    pageCounter=1
    finished = False

    inlineCommentedFile = []
    reviewCommentList=[]
    
    # primary keys to reduce time while processing already encountered data  
    primary_keys = set()
    cursor = mydb.cursor()
    sql = "select id from review_comments where project_name ='"+PROJECT+"'"+"and change_trigger is not NULL" 
    ## comment id of that project that is processed
    cursor.execute(sql)
    lst = cursor.fetchall()
    primary_keys = set(val[0] for val in lst)
    #print(primary_keys)
    cursor.close()
    
    primary_pull_keys = set()
    cursor = mydb.cursor()
    sql = "select pull_no from review_comments where project_name ='"+PROJECT+"'"+"and change_trigger is NULL"
    ## pull no's of those comments not processed
    cursor.execute(sql)
    lst = cursor.fetchall()
    primary_pull_keys = set(val[0] for val in lst)
    #print(primary_keys)
    cursor.close()
    
    state = "open"
    while not finished:
        #print(state+ "comes")
        pulls = get(BASE+"pulls?page={}&per_page=100&state={}".format(pageCounter, state))
        pageCounter+=1
        if isLast(pulls):
            finished =True
        pullsJson = pulls.json()

        for pull in pullsJson:
            try:
                pull_number = pull['number']
                if pull_number not in primary_pull_keys:
                    continue
                print("pull number = {}".format(pull['number']))
                #pull_commit = pull['base']['sha']
                pull_commit = pull['merge_commit_sha']
                if pull_commit is None:
                    continue
                pull_review_comments = pull['_links']['review_comments']['href']
                pageCounterInside = 1
                finishedInside = False
                
                '''
                for this pull we get all the commits on this pull so that we can track the changes on the commented files
                to claculate changes triggered or not  
                '''
                pull_commits = []
                InpageCounter=1
                Infinished = False
                while not Infinished:
                    #print(pull['_links']['commits']['href']+"?page={}&per_page=100&state={}".format(InpageCounter, state))
                    pulls = get(pull['_links']['commits']['href']+"?page={}&per_page=100&state={}".format(InpageCounter, state))

                    if isLast(pulls):
                        Infinished =True
                    for commit in get(pull['_links']['commits']['href']+"?page={}&per_page=100&state={}".format(InpageCounter, state)).json():
                        commit_hash = commit['sha']
                        pull_commits.append(commit_hash)
                    InpageCounter+=1
                '''
                get all the comments on this pull request
                '''
                while not finishedInside:
                    reviewComment = get(pull_review_comments+"?page={}&per_page=100".format(pageCounterInside))
                    pageCounterInside+=1
                    if isLast(reviewComment):
                        finishedInside =True
                    reviewCommentsJson = reviewComment.json()
                    
                    tracked_files = {}
                    line_no = {}
                    raw_location = {}
                    pull_commit_table = {}
                    comment_id = {}
                    diff = {}
                    '''
                    for each of those comments tract in which file what position that comment is done and store necessary information 
                     like raw file contents url to use change_calculation() function 
                    '''
                    for rc in reviewCommentsJson:
                        #print("rc path"+rc['path'])
                        if 'in_reply_to_id' in rc.keys():
                            continue
                        if rc['id'] in primary_keys:
                            continue
                        tracked_files[rc['path']] = []
                        line_no[rc['path']] = rc['original_position']
                        pull_commit_table[rc['path']] = pull_commit
                        diff[rc['path']] = rc['diff_hunk']
                        if rc['path'] in comment_id.keys():
                            #comment_id[rc['path']].append((rc['id'], rc['commit_id']))
                            comment_id[rc['path']] = rc['id']
                        else:
                            comment_id[rc['path']] = rc['id']
                            #comment_id[rc['path']] = []
                            #comment_id[rc['path']].append((rc['id'], rc['commit_id']))

                        file_list_json = get(BASE+'commits/'+pull_commit).json()
                        if 'documentation_url' in file_list_json.keys():
                            continue
                        file_list = file_list_json['files']
                        for file in file_list:
                            if file['filename'] in tracked_files.keys():
                                link = file['raw_url']
                                # this is weirdly necessary because the link github api gives doesnot actually get us the actual file 
                                # but changing this like done below gives us what we want
                                link = link.replace('raw/', '')
                                link = link.replace('', '/raw')
                                raw_location[file['filename']] = link # why is raw_location empty

                        '''
                        for each of those commits in the pull request we already stored way before we check all the files that are 
                        changed in this commit. if any of those files are among the file we are tracking(a review comment is done in this file)
                        then we append it on the tracked files dictory list. the structure is like this of tracked_files dictionary-> 
                        key                         ->  value
                        [review_comment_done_file_name]    ->  [file_1_commit_1_location, file_1_commit_3_location,file_1_commit_4_location etc ] maybe commit 2 didnt change our tracked file
                        key is only the file name not location because raw_location is a dictionary as key= file name , and value = raw location url of that file of this pull commit of the snapshot
                        '''
                        commit_counter= 0
                        for commit_hash in pull_commits:
                            commit_counter+=1
                            commitDict = parse_commit(get(BASE+'commits/'+commit_hash).json(),pull_no=pull['number'],commit_no=commit_counter,is_last_commit = (len(pull_commits)==commit_counter))## here parcing happening

                            file_list = get(BASE+'commits/'+commit_hash).json()['files']
                            #pprint(file_list)
                            for file in file_list:
                                #print(pull['number'])
                                if file['filename'] in tracked_files.keys():
                                    location = file['filename']
                                    link = file['raw_url']
                                    link = link.replace('raw/', '')
                                    link = link.replace('', '/raw')
                                    tracked_files[location].append(link)
                        '''
                        for each of those files (actually this will be only one file as one review comment can only be fin one file)
                        use change_calculation function to check change triggered or not
                        '''
                        for file in tracked_files.keys():
                            value = 9999
                            for compare_file in tracked_files[file]:
                                if file in raw_location.keys():
                                    #print(raw_location[file])
                                    #print(diff[file])
                                    s = diff[file][:30]
                                    s = s.split("@@")
                                    if len(s)<2:
                                        continue
                                    s = s[1].split(',')
                                    if len(s)<3:
                                        continue
                                    comment_line_width = int(s[2].strip())
                                    #print(s)
                                    s = s[1].split(' ')
                                    comment_line_position = int(s[1][1:])
                                    if(comment_line_width<10):
                                        comment_line_width = 10

                                    if(comment_line_width<=30):
                                        print("raw_location file = ", raw_location[file])
                                        print("compare_file = ", compare_file)
                                        value = change_calculation(get_raw(raw_location[file]).text,get_raw(compare_file).text,comment_line_position+(comment_line_width//2),comment_line_width//2)  
                                    if value != 9999:
                                        break
                                else:
                                    print("##########not in raw location############")       
                            print(value, "comment id = ", comment_id[file])
                            cursor = mydb.cursor()
                            sql = "UPDATE review_comments SET change_trigger={} where id={} and project_name ='{}'".format(value,comment_id[file],PROJECT)
                            #print(sql)
                            cursor.execute(sql)
                            cursor.close()
            except Exception as e:
                print("$$$ CATCH ERROR "+ e)
                print(PROJECT , "line no 435")
                continue
                    
        if finished and state=='open':
            finished = False
            pageCounter=1
            state = 'closed'
    
    ############### change trigger calculation in review_comment table ends ########
    
    
    # comments on a file for pull request there is pull request comments and pull request review comments
    
    
    ########### comments(not review comments rater comments on whole file or comments on issue) mining starts###
    commentList = []
    pageCounter=1
    finished = False
    ct= 0
    
    primary_keys = set()
    cursor = mydb.cursor()
    sql = "select id from comments where project_name ='"+PROJECT+"'"
    cursor.execute(sql)
    lst = cursor.fetchall()
    primary_keys = set(val[0] for val in lst)
    cursor.close()
    ## for a given comment json it extracts relevent informations and inserts them into the comments table ##### 
    def parce_comment(comment):
        if comment['id'] not in primary_keys:
            commentDict = {}
            commentDict['project_name'] = PROJECT
            commentDict['id'] = comment['id']
            #commentDict['id'] = str(comment['id'])
            commentDict['body'] = comment['body'].replace("'", "")
            commentDict['body'] = commentDict['body'].replace("\\", "")
            commentDict['body'] = commentDict['body'].replace('"', '')
            #print(comment['body'])
            commentDict['created_at']=str(datetime.strptime(comment['created_at'], '%Y-%m-%dT%H:%M:%SZ'))
            commentDict['user_id'] = comment['user']['id']

            cursor = mydb.cursor()
            sql = "INSERT INTO comments (project_name, id, body, created_at, user_id) VALUES ("            +"'"+commentDict['project_name']+"',"+"{}".format(commentDict['id'])+",'"+commentDict['body']+"','"+commentDict['created_at']+"','"+str(commentDict['user_id'])+"') ON DUPLICATE KEY UPDATE body='{}'".format(commentDict['body'])
            #print(sql)
            cursor.execute(sql)
            primary_keys.add(commentDict['id'])
            cursor.close()
            #print(reviewCommentDic)
            #return commentDict
    ##### comments on whole file or just in conversation not review comments mining starts #####
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
                    try:
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
                    except Exception as e:
                        print("$$$ CATCH ERROR "+ e)
                        print(PROJECT , "line no 527")
                        continue
    ### conversation comments or whole file comments mingin ends#####
    
    
    ### issue comments mining starts ######
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
                if isLast(commentsInIssue):
                    finishedInsize = True
                commentsInIssueList = commentsInIssue.json()
                for comment in commentsInIssueList:
                    try:
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
                    except Exception as e:
                        print("$$$ CATCH ERROR "+ e)
                        print(PROJECT , "line no 573")
                        continue
    ### issue comments mining ends ######
    ########### comments(not review comments rater comments on whole file or comments on issue) mining ends###
    
    ##### commits mining starts #######
    primary_keys = set()
    cursor = mydb.cursor()
    sql = "select id from commits"
    cursor.execute(sql)
    lst = cursor.fetchall()
    primary_keys = set(val[0] for val in lst)
    #print(primary_keys)
    cursor.close()
    
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

        if bool(ci['author']) and ci['author'] is not None:
            commitInfoDict['author_id'] = ci['author']['id']
        else:
            commitInfoDict['author_id'] = "NULL"
            #print("author id null")

        commitInfoDict['committer_name'] = ci['commit']['committer']['name']
        commitInfoDict['committer_email'] = ci['commit']['committer']['email']

        if bool(ci['committer']) and ci['committer'] is not None:
            commitInfoDict['committer_id'] = ci['committer']['id']
        else:
            commitInfoDict['committer_id'] = "NULL"

        commitInfoDict['message'] = str(ci['commit']['message']).replace("'", "")
        commitInfoDict['message'] = commitInfoDict['message'].replace("\\", "")
        commitInfoDict['message'] = commitInfoDict['message'].replace('"', '')
        
        if len(commitInfoDict['message'])>5000:
            commitInfoDict['message'] = commitInfoDict['message'][:5000]
        
        if commitInfoDict['commit_id'] not in primary_keys:
            cursor = mydb.cursor()
            sql = "INSERT INTO commits (id,author_name,author_email,date, author_id,committer_name,committer_email,committer_id, message) VALUES ("+            "'"+commitInfoDict['commit_id']+"','"+commitInfoDict['author_name']+"','"+commitInfoDict['author_email']+"','"+commitInfoDict['date']+"',"+"{}".format(commitInfoDict['author_id'])+",'"+commitInfoDict['committer_name']+"','"+commitInfoDict['committer_email']+"',"+"{}".format(commitInfoDict['committer_id'])+",'"+commitInfoDict['message']+"') ON DUPLICATE KEY UPDATE message='{}'".format(commitInfoDict['message'])
            #print(sql)
            
            cursor.execute(sql)
            primary_keys.add(commitInfoDict['commit_id'])
            #if commitInfoDict['author_id'] == "NULL":
                #print("author id null")
            cursor.close()
        author = {}
        author['id'] = commitInfoDict['author_id'] 
        author['name'] = commitInfoDict['author_name'] 
        author['email'] = commitInfoDict['author_email'] 
        if author not in userList:
            userList.append(author)
        author = {}
        author['id'] = commitInfoDict['committer_id'] 
        author['name'] = commitInfoDict['committer_name'] 
        author['email'] = commitInfoDict['committer_email'] 
        if author not in userList:
            userList.append(author) 
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
                try:
                    parse_commit(ci)
                    commitInfoDict = ci
                    commit_count+=1
                except Exception as e:
                    print("$$$ CATCH ERROR "+ e)
                    print(PROJECT , "line no 678")
                    continue
                
        print(commit_count)
        
    ##### pull requests information mining in pulls table starts #######
    pullInfo = []
    pageCounter=1
    finished = False
    
    primary_keys = set()
    cursor = mydb.cursor()
    sql =  "select id from pulls where project_name ='"+PROJECT+"'"
    cursor.execute(sql)
    lst = cursor.fetchall()
    primary_keys = set(val[0] for val in lst)
    #print(primary_keys)
    cursor.close()
    
    state = "open"
    while not finished:
        pullsJson = get(BASE+"pulls?page={}&per_page=100&state={}".format(pageCounter,state))
        #print(BASE+"pulls?page={}&per_page=100&state={}".format(pageCounter,state))
        pageCounter+=1
        #print("comes")
        if isLast(pullsJson):
            finished =True
        pullsJsonList = pullsJson.json()
   
        for pull in pullsJsonList:#[4:5]: #many pull request for one project
            #pprint(len(get(pull['_links']['commits']['href']).json()))
            #break
            try:
                if str(pull['id']) in primary_keys:
                    continue
                pull_dict = {}
                pull_dict['project_name'] =  PROJECT
                pull_dict['id'] =str(pull['id'])
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
            except Exception as e:
                print("$$$ CATCH ERROR "+ e)
                print(PROJECT , "line no 799")
                continue
            cursor = mydb.cursor()
            sql = "INSERT INTO pulls ( project_name, id,commit_id, user_id,state, number,created_at) VALUES ("+"'"+pull_dict['project_name']+"','"+pull_dict['id']+"','"+pull_dict['commit_id']+"',"+"{}".format(pull_dict['user_id'])+",'"+pull_dict['state']+"','"+str(pull_dict['number'])+"','"+pull_dict['created_at']+"') ON DUPLICATE KEY UPDATE state='{}'".format(pull_dict['state'])
            cursor.execute(sql)
            primary_keys.add(pull_dict['id'])
            cursor.close()
            
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
                
    ##### pull requests information mining in pulls table ends #######  
    
    #### userList mining in users table starts ################
    primary_keys = set()
    cursor = mydb.cursor()
    sql =  "select id from users"
    cursor.execute(sql)
    lst = cursor.fetchall()
    primary_keys = set(val[0] for val in lst)
    #print(primary_keys)
    cursor.close()
    ## userList was define globally whenever a new user found to comment or commit or review or create pull request his/her id was saved
    ## and finally this id is being merged now
    
    for user in userList:
        try:
            if user['id'] in primary_keys or user['id']=="NULL":
                continue
            cursor = mydb.cursor()
            sql = "INSERT INTO users (id, name, email) VALUES ("+"'"+str(user['id'])+"','"+user['name']+"','"+user['email']+"') ON DUPLICATE KEY UPDATE email='{}'".format(user['email'])
            cursor.execute(sql)
            primary_keys.add(user['id'])
            cursor.close()
        except Exception as e:
            print("$$$ CATCH ERROR "+ e)
            print(PROJECT , "line no 853")
            continue
    #### userList mining in users table ends ################
# this function accepts a user as different users can have differnt passwords this adds functionality to mine from 
# multiple user data with multiple user repo same time 

def github_miner(request, dbname):
    print("Inside Github Miner.")
    user = str(request.POST.get('githubUsername', False))
    pw = str(request.POST.get('githubPassword', False))
    DBUser = str(request.POST.get('dbUsername', False))
    DBPassword = str(request.POST.get('dbPassword', False))
    DBHost = "localhost" #str(request.POST.get('dbHost', False))
    API = str(request.POST.get('githubURL', False))

    repl = API+"repos/"
    mydb = mysql.connector.connect(
          host=DBHost,
          user=DBUser,
          passwd=DBPassword,
          database=dbname
        )
    global user_auth
    global password
    ## these if and elif blocks changes the global user_auth and passwords variables and so auth variable values inside
    ## get and get_raw functoins also changes and mine goes on after changing the user

    user_auth = user
    password = pw
    c = 0
    import os
    repoPageCounte.r=1
    repoFinished = False
    while not repoFinished:
        repoListReq = get(API+"user/repos?page={}&per_page=100".format(repoPageCounter))
        repoPageCounter+=1
        if isLast(repoListReq):
            repoFinished =True
        for project in repoListReq.json():
            PROJECT = project['full_name']+'/'
            BASE = repl+PROJECT
            #print(os.getcwd())
            mine(BASE, PROJECT, mydb, API)
            c+=1
            #return 0
            






