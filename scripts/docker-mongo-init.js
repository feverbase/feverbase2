db.auth('root', 'root')

db = db.getSiblingDB('dev')

db.createUser({
  user: 'dev',
  pwd: 'dev',
  roles: [
    {
      role: 'readWrite',
      db: 'dev',
    },
  ],
});
