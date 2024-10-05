from pymongo import MongoClient

class Database:
    def __init__(self):
        self.client = MongoClient('localhost', 27017)
        self.db = self.client['tiktok']
        self.collection = self.db['video_list']

    def insert(self, data):
        self.collection.insert_one(data)
    
    def insert_many(self, data):
        self.collection.insert_many(data)

    def find(self, query):
        return self.collection.find(query)

    def update(self, query, data):
        self.collection.update_one(query, data)

    def delete(self, query):
        self.collection.delete_one(query)
    
    def on_close(self):
        self.client.close()

if __name__ == "__main__":
    db = Database()
    db.insert({"name": "John Doe", "age": 30})
    print(db.find({"name": "John Doe"}))
    db.on_close()