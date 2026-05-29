#!/usr/bin/env python3
import sqlite3
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timedelta

DB_PATH = 'main.db'

MAINTENANCE_TYPES = {
    '机油更换': {'km_interval': 5000, 'month_interval': 6},
    '轮胎更换': {'km_interval': 40000, 'month_interval': 36},
    '刹车检查': {'km_interval': 10000, 'month_interval': 12},
    '全面保养': {'km_interval': 20000, 'month_interval': 12},
    '其他': {'km_interval': 0, 'month_interval': 0}
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS vehicles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  plate_number TEXT UNIQUE NOT NULL,
                  brand_model TEXT NOT NULL,
                  owner_name TEXT NOT NULL,
                  phone TEXT NOT NULL,
                  purchase_date TEXT NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS maintenance_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  vehicle_id INTEGER NOT NULL,
                  maintenance_type TEXT NOT NULL,
                  date TEXT NOT NULL,
                  mileage INTEGER NOT NULL,
                  cost INTEGER NOT NULL,
                  notes TEXT,
                  FOREIGN KEY (vehicle_id) REFERENCES vehicles(id))''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_next_maintenance(record):
    mtype = record['maintenance_type']
    config = MAINTENANCE_TYPES.get(mtype, MAINTENANCE_TYPES['其他'])
    
    if config['km_interval'] == 0 and config['month_interval'] == 0:
        return None
    
    record_date = datetime.strptime(record['date'], '%Y-%m-%d')
    next_date = record_date + timedelta(days=30 * config['month_interval'])
    next_mileage = record['mileage'] + config['km_interval']
    
    today = datetime.now()
    days_overdue = (today - next_date).days
    mileage_overdue = max(0, record['mileage'] - next_mileage)
    is_due = days_overdue >= 0 or mileage_overdue > 0
    
    return {
        'next_date': next_date.strftime('%Y-%m-%d'),
        'next_mileage': next_mileage,
        'km_interval': config['km_interval'],
        'month_interval': config['month_interval'],
        'is_due': is_due,
        'days_overdue': days_overdue,
        'mileage_overdue': mileage_overdue
    }

class RequestHandler(BaseHTTPRequestHandler):
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/':
            self.serve_static_file('index.html')
        elif path == '/app.js':
            self.serve_static_file('app.js')
        elif path == '/api/vehicles':
            self.get_vehicles()
        elif path.startswith('/api/vehicles/'):
            vehicle_id = int(path.split('/')[-1])
            self.get_vehicle(vehicle_id)
        elif path.startswith('/api/vehicles/') and '/history' in path:
            vehicle_id = int(path.split('/')[3])
            self.get_vehicle_history(vehicle_id)
        elif path == '/api/maintenance-records':
            self.get_maintenance_records()
        elif path == '/api/reminders':
            self.get_reminders()
        elif path == '/api/maintenance-types':
            self.get_maintenance_types()
        else:
            self.send_response(404)
            self.end_headers()
    
    def serve_static_file(self, filename):
        if os.path.exists(filename):
            self.send_response(200)
            if filename.endswith('.html'):
                self.send_header('Content-Type', 'text/html; charset=utf-8')
            elif filename.endswith('.js'):
                self.send_header('Content-Type', 'application/javascript; charset=utf-8')
            self.end_headers()
            with open(filename, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
    
    def get_maintenance_types(self):
        types_list = []
        for name, config in MAINTENANCE_TYPES.items():
            types_list.append({
                'name': name,
                'km_interval': config['km_interval'],
                'month_interval': config['month_interval']
            })
        self.send_json_response(types_list)
    
    def get_vehicles(self):
        conn = get_db_connection()
        vehicles = conn.execute('SELECT * FROM vehicles ORDER BY id DESC').fetchall()
        conn.close()
        self.send_json_response([dict(v) for v in vehicles])
    
    def get_vehicle(self, vehicle_id):
        conn = get_db_connection()
        vehicle = conn.execute('SELECT * FROM vehicles WHERE id = ?', (vehicle_id,)).fetchone()
        conn.close()
        if vehicle:
            self.send_json_response(dict(vehicle))
        else:
            self.send_json_response({'error': 'Vehicle not found'}, 404)
    
    def get_vehicle_history(self, vehicle_id):
        conn = get_db_connection()
        records = conn.execute('''
            SELECT mr.*, v.plate_number, v.brand_model 
            FROM maintenance_records mr 
            JOIN vehicles v ON mr.vehicle_id = v.id 
            WHERE v.id = ? 
            ORDER BY mr.date DESC, mr.id DESC
        ''', (vehicle_id,)).fetchall()
        conn.close()
        
        result = []
        for r in records:
            record_dict = dict(r)
            next_maint = calculate_next_maintenance(record_dict)
            if next_maint:
                record_dict.update(next_maint)
            result.append(record_dict)
        
        self.send_json_response(result)
    
    def get_maintenance_records(self):
        conn = get_db_connection()
        records = conn.execute('''
            SELECT mr.*, v.plate_number, v.brand_model 
            FROM maintenance_records mr 
            JOIN vehicles v ON mr.vehicle_id = v.id 
            ORDER BY mr.date DESC, mr.id DESC
        ''').fetchall()
        conn.close()
        
        result = []
        for r in records:
            record_dict = dict(r)
            next_maint = calculate_next_maintenance(record_dict)
            if next_maint:
                record_dict.update(next_maint)
            result.append(record_dict)
        
        self.send_json_response(result)
    
    def get_reminders(self):
        conn = get_db_connection()
        vehicles = conn.execute('SELECT * FROM vehicles').fetchall()
        today = datetime.now()
        
        reminders = []
        
        for vehicle in vehicles:
            vehicle_dict = dict(vehicle)
            
            for mtype, config in MAINTENANCE_TYPES.items():
                if config['km_interval'] == 0 and config['month_interval'] == 0:
                    continue
                
                latest = conn.execute('''
                    SELECT * FROM maintenance_records 
                    WHERE vehicle_id = ? AND maintenance_type = ? 
                    ORDER BY date DESC, id DESC LIMIT 1
                ''', (vehicle['id'], mtype)).fetchone()
                
                if latest:
                    record_date = datetime.strptime(latest['date'], '%Y-%m-%d')
                    next_date = record_date + timedelta(days=30 * config['month_interval'])
                    next_mileage = latest['mileage'] + config['km_interval']
                    last_mileage = latest['mileage']
                else:
                    next_date = datetime.strptime(vehicle['purchase_date'], '%Y-%m-%d') + timedelta(days=30 * config['month_interval'])
                    next_mileage = config['km_interval']
                    last_mileage = 0
                
                days_overdue = (today - next_date).days
                mileage_overdue = max(0, last_mileage - next_mileage)
                
                is_due = days_overdue >= 0 or mileage_overdue > 0
                is_soon = (not is_due) and (days_overdue >= -30 or (next_mileage - last_mileage) <= 1000)
                
                if is_due or is_soon:
                    reminders.append({
                        'vehicle_id': vehicle['id'],
                        'plate_number': vehicle['plate_number'],
                        'brand_model': vehicle['brand_model'],
                        'owner_name': vehicle['owner_name'],
                        'phone': vehicle['phone'],
                        'maintenance_type': mtype,
                        'next_date': next_date.strftime('%Y-%m-%d'),
                        'next_mileage': next_mileage,
                        'days_overdue': days_overdue,
                        'mileage_overdue': mileage_overdue,
                        'last_mileage': last_mileage,
                        'is_due': is_due,
                        'status': 'overdue' if is_due else 'soon',
                        'km_interval': config['km_interval'],
                        'month_interval': config['month_interval']
                    })
        
        conn.close()
        
        reminders.sort(key=lambda x: (x['status'], -x['days_overdue'], -x['mileage_overdue']))
        self.send_json_response(reminders)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = parse_qs(body)
            data = {k: v[0] for k, v in data.items()}
        
        if path == '/api/vehicles':
            self.create_vehicle(data)
        elif path == '/api/maintenance-records':
            self.create_maintenance_record(data)
        else:
            self.send_json_response({'error': 'Not found'}, 404)
    
    def create_vehicle(self, data):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO vehicles (plate_number, brand_model, owner_name, phone, purchase_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (data['plate_number'], data['brand_model'], data['owner_name'], 
                  data['phone'], data['purchase_date']))
            conn.commit()
            vehicle_id = cursor.lastrowid
            conn.close()
            self.send_json_response({'id': vehicle_id, 'message': '创建成功'})
        except sqlite3.IntegrityError:
            self.send_json_response({'error': '车牌号已存在'}, 400)
        except Exception as e:
            self.send_json_response({'error': str(e)}, 400)
    
    def create_maintenance_record(self, data):
        try:
            maintenance_type = data['maintenance_type']
            if maintenance_type not in MAINTENANCE_TYPES:
                self.send_json_response({'error': '保养类型必须是：' + '、'.join(MAINTENANCE_TYPES.keys())}, 400)
                return
            
            cost = int(data['cost'])
            if cost < 0:
                self.send_json_response({'error': '费用不能为负数'}, 400)
                return
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO maintenance_records (vehicle_id, maintenance_type, date, mileage, cost, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (data['vehicle_id'], maintenance_type, data['date'],
                  int(data['mileage']), cost, data.get('notes', '')))
            conn.commit()
            record_id = cursor.lastrowid
            conn.close()
            self.send_json_response({'id': record_id, 'message': '创建成功'})
        except Exception as e:
            self.send_json_response({'error': str(e)}, 400)
    
    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path.startswith('/api/vehicles/'):
            vehicle_id = int(path.split('/')[-1])
            self.delete_vehicle(vehicle_id)
        elif path.startswith('/api/maintenance-records/'):
            record_id = int(path.split('/')[-1])
            self.delete_maintenance_record(record_id)
        else:
            self.send_json_response({'error': 'Not found'}, 404)
    
    def delete_vehicle(self, vehicle_id):
        try:
            conn = get_db_connection()
            conn.execute('DELETE FROM maintenance_records WHERE vehicle_id = ?', (vehicle_id,))
            conn.execute('DELETE FROM vehicles WHERE id = ?', (vehicle_id,))
            conn.commit()
            conn.close()
            self.send_json_response({'message': '删除成功'})
        except Exception as e:
            self.send_json_response({'error': str(e)}, 400)
    
    def delete_maintenance_record(self, record_id):
        try:
            conn = get_db_connection()
            conn.execute('DELETE FROM maintenance_records WHERE id = ?', (record_id,))
            conn.commit()
            conn.close()
            self.send_json_response({'message': '删除成功'})
        except Exception as e:
            self.send_json_response({'error': str(e)}, 400)
    
    def log_message(self, format, *args):
        pass

def main():
    init_db()
    port = 7600
    server = HTTPServer(('localhost', port), RequestHandler)
    print(f'服务器启动: http://localhost:{port}')
    server.serve_forever()

if __name__ == '__main__':
    main()
