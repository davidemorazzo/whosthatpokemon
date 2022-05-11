@echo off
cd "D:\Programmazione\Fiverr\whosthatpokemon"
call heroku pg:backups:capture postgresql-round-98059
call heroku pg:backups:download -o "HEROKU_CHARCOAL_BACKUP.dump"
echo Pg_restore local database
pg_restore -U postgres -d whosthatpokemon --clean HEROKU_CHARCOAL_BACKUP.dump
del "HEROKU_CHARCOAL_BACKUP.dump"
