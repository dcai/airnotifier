db = connect("mongodb://" + process.env.MONGO_SERVER + ":" + process.env.MONGO_PORT + "/app_studium");

// Today and Thirty days ago
var today = new Date();
var todayUnix = Math.floor((today.getTime()/1000)-21600); // -6 hours
var thirtydaysago  = todayUnix-2592000; // 30 days ago
var logsinfos = null;

// View stats for log:
var logsinfosbefore = db.logs.stats();
print('========== '+today+' ==========');
print('========== STATS BEFORE QUERY ==========');
print('ns : '+logsinfosbefore['ns']);
print('size : '+logsinfosbefore['size']);
print('count : '+logsinfosbefore['count']);
print('avgObjSize : '+logsinfosbefore['avgObjSize']);
print('storageSize : '+logsinfosbefore['storageSize']);

// DELETE OLD LOGS:
db.logs.remove({
    "created" : {
      $lte: thirtydaysago, // lt less than
    }
  });

// View stats for log:
var logsinfos = db.logs.stats();
print('========== STATS AFTER QUERY ==========');
print('ns : '+logsinfos['ns']);
print('size : '+logsinfos['size']);
print('count : '+logsinfos['count']);
print('avgObjSize : '+logsinfos['avgObjSize']);
print('storageSize : '+logsinfos['storageSize']);
