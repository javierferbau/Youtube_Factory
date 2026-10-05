const sqlite3 = require('/usr/local/lib/node_modules/n8n/node_modules/sqlite3');
const db = new sqlite3.Database('/home/node/.n8n/database.sqlite');

db.get('SELECT workflowData FROM execution_data WHERE executionId=73055', (err, row) => {
  if (err || !row) {
    console.error('Error fetching execution 73055:', err);
    process.exit(1);
  }
  const wf = JSON.parse(row.workflowData);
  const connectionsObj = wf.connections;
  const connJsonStr = JSON.stringify(connectionsObj);
  
  console.log('Restoring full connections object with', Object.keys(connectionsObj).length, 'keys');
  
  db.run('UPDATE workflow_entity SET connections = ? WHERE id = ?', [connJsonStr, 'TY375mNkv5eejIQi'], (err2) => {
    if (err2) console.error('Error updating workflow_entity:', err2);
    db.run('UPDATE workflow_history SET connections = ? WHERE workflowId = ?', [connJsonStr, 'TY375mNkv5eejIQi'], (err3) => {
      if (err3) console.error('Error updating workflow_history:', err3);
      console.log('Successfully restored connections in workflow_entity and workflow_history!');
      db.close();
    });
  });
});
