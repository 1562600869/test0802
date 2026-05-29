const API_BASE = '/api';

document.addEventListener('DOMContentLoaded', function() {
    initTabs();
    loadMaintenanceTypes();
    loadVehicles();
    loadReminders();
    loadRecords();
    loadStats();
});

function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tab = this.dataset.tab;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            document.getElementById(tab).classList.add('active');
        });
    });
}

async function fetchAPI(url, options = {}) {
    try {
        const response = await fetch(API_BASE + url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || '请求失败');
        }
        return data;
    } catch (error) {
        alert(error.message);
        throw error;
    }
}

async function loadStats() {
    try {
        const [vehicles, records, reminders] = await Promise.all([
            fetchAPI('/vehicles'),
            fetchAPI('/maintenance-records'),
            fetchAPI('/reminders')
        ]);
        
        const overdueCount = reminders.filter(r => r.status === 'overdue').length;
        const totalCost = records.reduce((sum, r) => sum + r.cost, 0);
        
        document.getElementById('statsGrid').innerHTML = `
            <div class="stat-card">
                <div class="stat-number">${vehicles.length}</div>
                <div class="stat-label">车辆总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${records.length}</div>
                <div class="stat-label">保养记录</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" style="color: ${overdueCount > 0 ? '#dc2626' : '#059669'}">${overdueCount}</div>
                <div class="stat-label">超期未保养</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">¥${(totalCost / 100).toFixed(2)}</div>
                <div class="stat-label">累计费用</div>
            </div>
        `;
    } catch (e) {
        console.error('加载统计失败', e);
    }
}

async function loadVehicles() {
    try {
        const vehicles = await fetchAPI('/vehicles');
        const table = document.getElementById('vehiclesTable');
        
        if (vehicles.length === 0) {
            table.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🚙</div>
                    <p>暂无车辆档案</p>
                    <p style="font-size: 13px; margin-top: 8px;">点击上方"添加车辆"开始录入</p>
                </div>
            `;
            return;
        }
        
        table.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>车牌号</th>
                        <th>品牌型号</th>
                        <th>车主姓名</th>
                        <th>手机号</th>
                        <th>购车日期</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${vehicles.map(v => `
                        <tr>
                            <td><span class="plate-number">${v.plate_number}</span></td>
                            <td>${v.brand_model}</td>
                            <td>${v.owner_name}</td>
                            <td>${v.phone}</td>
                            <td>${v.purchase_date}</td>
                            <td>
                                <button class="btn btn-secondary" onclick="viewHistory(${v.id})">查看历史</button>
                                <button class="btn btn-danger" onclick="deleteVehicle(${v.id})">删除</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
        const vehicleSelect = document.getElementById('vehicleSelect');
        vehicleSelect.innerHTML = '<option value="">请选择车辆</option>' + 
            vehicles.map(v => `<option value="${v.id}">${v.plate_number} - ${v.brand_model}</option>`).join('');
    } catch (e) {
        console.error('加载车辆失败', e);
    }
}

async function loadMaintenanceTypes() {
    try {
        const types = await fetchAPI('/maintenance-types');
        const select = document.getElementById('maintenanceTypeSelect');
        select.innerHTML = '<option value="">请选择保养类型</option>' + 
            types.map(t => `<option value="${t.name}">${t.name} (每${t.km_interval}km或${t.month_interval}个月)</option>`).join('');
    } catch (e) {
        console.error('加载保养类型失败', e);
    }
}

async function loadReminders() {
    try {
        const reminders = await fetchAPI('/reminders');
        const table = document.getElementById('remindersTable');
        
        if (reminders.length === 0) {
            table.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">✅</div>
                    <p>暂无到期保养提醒</p>
                    <p style="font-size: 13px; margin-top: 8px;">所有车辆保养状态良好</p>
                </div>
            `;
            return;
        }
        
        table.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>车牌号</th>
                        <th>品牌型号</th>
                        <th>车主</th>
                        <th>保养类型</th>
                        <th>建议日期</th>
                        <th>建议里程</th>
                        <th>状态</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${reminders.map(r => `
                        <tr>
                            <td><span class="plate-number">${r.plate_number}</span></td>
                            <td>${r.brand_model}</td>
                            <td>${r.owner_name}<br><small>${r.phone}</small></td>
                            <td>${r.maintenance_type}</td>
                            <td class="${r.status === 'overdue' ? 'warning-text' : ''}">${r.next_date}</td>
                            <td class="${r.status === 'overdue' && r.mileage_overdue > 0 ? 'warning-text' : ''}">${r.next_mileage.toLocaleString()} km</td>
                            <td>
                                <span class="badge badge-${r.status}">
                                    ${r.status === 'overdue' ? '已超期' : '即将到期'}
                                </span>
                                ${r.status === 'overdue' ? `<br><small style="color:#999;margin-top:4px;display:inline-block;">超期${r.days_overdue}天${r.mileage_overdue > 0 ? ' / 超'+r.mileage_overdue+'km' : ''}</small>` : ''}
                            </td>
                            <td>
                                <button class="btn btn-secondary" onclick="quickAddRecord(${r.vehicle_id}, '${r.maintenance_type}')">添加保养</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (e) {
        console.error('加载提醒失败', e);
    }
}

async function loadRecords() {
    try {
        const records = await fetchAPI('/maintenance-records');
        const table = document.getElementById('recordsTable');
        
        if (records.length === 0) {
            table.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📝</div>
                    <p>暂无保养记录</p>
                    <p style="font-size: 13px; margin-top: 8px;">点击上方"添加记录"开始录入</p>
                </div>
            `;
            return;
        }
        
        table.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>车牌号</th>
                        <th>保养类型</th>
                        <th>日期</th>
                        <th>里程</th>
                        <th>费用</th>
                        <th>下次保养</th>
                        <th>备注</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${records.map(r => `
                        <tr>
                            <td><span class="plate-number">${r.plate_number}</span></td>
                            <td>${r.maintenance_type}</td>
                            <td>${r.date}</td>
                            <td>${r.mileage.toLocaleString()} km</td>
                            <td class="cost">¥${(r.cost / 100).toFixed(2)}</td>
                            <td>
                                ${r.next_date ? `
                                    <div>${r.next_date}</div>
                                    <small style="color:#999">或 ${r.next_mileage.toLocaleString()} km</small>
                                ` : '-'}
                            </td>
                            <td><small>${r.notes || '-'}</small></td>
                            <td>
                                <button class="btn btn-danger" onclick="deleteRecord(${r.id})">删除</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (e) {
        console.error('加载记录失败', e);
    }
}

async function viewHistory(vehicleId) {
    try {
        const [vehicle, history] = await Promise.all([
            fetchAPI('/vehicles/' + vehicleId),
            fetchAPI('/vehicles/' + vehicleId + '/history')
        ]);
        
        document.getElementById('vehicleInfo').innerHTML = `
            <p><strong>车牌号：</strong><span class="plate-number">${vehicle.plate_number}</span></p>
            <p><strong>品牌型号：</strong>${vehicle.brand_model}</p>
            <p><strong>车主：</strong>${vehicle.owner_name} (${vehicle.phone})</p>
            <p><strong>购车日期：</strong>${vehicle.purchase_date}</p>
        `;
        
        const table = document.getElementById('historyTable');
        if (history.length === 0) {
            table.innerHTML = `
                <div class="empty-state" style="padding: 30px;">
                    <div class="empty-state-icon" style="font-size: 36px;">📭</div>
                    <p>暂无保养记录</p>
                </div>
            `;
        } else {
            table.innerHTML = `
                <table>
                    <thead>
                        <tr>
                            <th>日期</th>
                            <th>保养类型</th>
                            <th>里程</th>
                            <th>费用</th>
                            <th>下次保养</th>
                            <th>备注</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${history.map(r => `
                            <tr>
                                <td>${r.date}</td>
                                <td>${r.maintenance_type}</td>
                                <td>${r.mileage.toLocaleString()} km</td>
                                <td class="cost">¥${(r.cost / 100).toFixed(2)}</td>
                                <td>
                                    ${r.next_date ? `
                                        <div>${r.next_date}</div>
                                        <small style="color:#999">或 ${r.next_mileage.toLocaleString()} km</small>
                                    ` : '-'}
                                </td>
                                <td><small>${r.notes || '-'}</small></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
        
        document.getElementById('historyModal').classList.add('active');
    } catch (e) {
        console.error('加载历史失败', e);
    }
}

function closeHistoryModal() {
    document.getElementById('historyModal').classList.remove('active');
}

function openVehicleModal() {
    document.getElementById('vehicleForm').reset();
    document.getElementById('vehicleModalTitle').textContent = '添加车辆';
    document.getElementById('vehicleModal').classList.add('active');
}

function closeVehicleModal() {
    document.getElementById('vehicleModal').classList.remove('active');
}

async function saveVehicle(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    try {
        await fetchAPI('/vehicles', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        closeVehicleModal();
        loadVehicles();
        loadStats();
    } catch (e) {
        console.error('保存车辆失败', e);
    }
}

async function deleteVehicle(id) {
    if (!confirm('确定要删除此车辆吗？相关保养记录也将被删除。')) return;
    
    try {
        await fetchAPI('/vehicles/' + id, { method: 'DELETE' });
        loadVehicles();
        loadRecords();
        loadReminders();
        loadStats();
    } catch (e) {
        console.error('删除车辆失败', e);
    }
}

function openRecordModal() {
    document.getElementById('recordForm').reset();
    document.getElementById('recordModal').classList.add('active');
    const today = new Date().toISOString().split('T')[0];
    document.querySelector('#recordForm input[name="date"]').value = today;
}

function quickAddRecord(vehicleId, type) {
    document.getElementById('recordForm').reset();
    document.getElementById('vehicleSelect').value = vehicleId;
    document.getElementById('maintenanceTypeSelect').value = type;
    const today = new Date().toISOString().split('T')[0];
    document.querySelector('#recordForm input[name="date"]').value = today;
    document.getElementById('recordModal').classList.add('active');
}

function closeRecordModal() {
    document.getElementById('recordModal').classList.remove('active');
}

async function saveRecord(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    try {
        await fetchAPI('/maintenance-records', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        closeRecordModal();
        loadRecords();
        loadReminders();
        loadStats();
    } catch (e) {
        console.error('保存记录失败', e);
    }
}

async function deleteRecord(id) {
    if (!confirm('确定要删除此记录吗？')) return;
    
    try {
        await fetchAPI('/maintenance-records/' + id, { method: 'DELETE' });
        loadRecords();
        loadReminders();
        loadStats();
    } catch (e) {
        console.error('删除记录失败', e);
    }
}
