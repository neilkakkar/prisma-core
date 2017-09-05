import sys
from pymongo import MongoClient


class PrismaDev:
    def __init__(self):
        self.db_connection = MongoClient(serverSelectionTimeoutMS=2000, connect=False)

    def main(self):
        if len(sys.argv) == 1:
            print('Run: prisma_dev.py drop')
            exit()
        if sys.argv[1] == 'drop':
            database_list = self.db_connection.database_names()
            for database in database_list:
                if database != 'local':
                    self._destroy_db(database)

    def _destroy_db(self, database):
        self.db_connection.drop_database(database)

# if this module is called directly then go to the entry point
if __name__ == '__main__':
    prisma_dev = PrismaDev()
    prisma_dev.main()
