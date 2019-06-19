import pymongo
client = pymongo.MongoClient(host='localhost', port=27017)
db = client['xxxxxxxxx'] #数据库名称
table = db['board']
def get_info():
    for ii in table.find():
        if 'xxx' in ii['content']:
            print('留言板的主人:', ii['owner'], '留言者:', ii['name'], '留言时间:', ii['time'], '留言内容:', ii['content'])
    else:
        print('无记录')
if __name__ == '__main__':
    get_info()