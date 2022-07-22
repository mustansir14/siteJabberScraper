from flask import Flask, json, request
from utility_files.DB import DB
import logging

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)

api = Flask(__name__)

def response( errors, data = None):
    isFail = True if isinstance(errors,list) and len(errors) > 0 else False
    errors = errors if isinstance(errors,list) else []
    return json.dumps( { 'success': ( not isFail ), 'errors': errors, 'data': ( None if isFail else data ) }, default=str )

@api.route('/api/v1/company', methods=['GET'])
def flush_company_data():
    if "name" not in request.args or len( request.args["name"] ) == 0:
        return json.dumps({"error" : "missing name argument"})
        
    db = DB()
    errors = []
    
    print(db.host, db.user, db.password, db.db )
        
    sql = 'select * from company where company_name=%s'
    
    rows = db.queryArray( sql, (request.args["name"],))
    if rows is None:
        errors.append( "Internal error" )
    elif len( rows ) == 0:
        errors.append( "No companies with such name" )
        
    return response( errors, rows )

if __name__ == "__main__":
    api.run( host='0.0.0.0', port=6000 )