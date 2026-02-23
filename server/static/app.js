async function listDevices(){
  const res = await fetch('/api/devices');
  const devices = await res.json();
  const ul = document.getElementById('devices');
  ul.innerHTML = '';
  devices.forEach(d=>{
    const li = document.createElement('li');
    li.textContent = `${d.name} (id: ${d.id}) online: ${d.online ? 'yes' : 'no'}`;
    const on = document.createElement('button'); on.textContent='ON'; on.onclick = ()=>sendCmd(d.id,'on');
    const off = document.createElement('button'); off.textContent='OFF'; off.onclick = ()=>sendCmd(d.id,'off');
    li.appendChild(on); li.appendChild(off);
    ul.appendChild(li);
  })
}

async function createDevice(){
  const name = document.getElementById('name').value;
  const vehicle = document.getElementById('vehicle').value || null;
  if(!name) return alert('name required');
  await fetch('/api/devices', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name, vehicle_id: vehicle})});
  document.getElementById('name').value=''; document.getElementById('vehicle').value='';
  listDevices();
}

async function sendCmd(device_id, action){
  await fetch('/api/command', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({device_id, action, relay:0})});
  alert('command sent');
}

document.getElementById('create').addEventListener('click', createDevice);
document.getElementById('refresh').addEventListener('click', listDevices);
window.addEventListener('load', listDevices);
