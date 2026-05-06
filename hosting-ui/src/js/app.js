const backend = "51.142.251.103"
const API = "http://"+backend+":9000";
let currentPath = "";

function loadDashboard() {
  document.getElementById("content").innerHTML = `
    <h2>Dashboard</h2>
    <p>Welcome to Hosting Panel</p>
  `;
}

function showCreate() {
  document.getElementById("content").innerHTML = `
    <h2>Create Site</h2>

    <input id="domain" placeholder="Domain"><br><br>
    <input id="name" placeholder="Site Name"><br><br>

    <label>PHP Version:</label><br>
    <select id="php_version">
      <option value="8.2">PHP 8.2</option>
      <option value="8.0">PHP 8.0</option>
      <option value="7.4">PHP 7.4</option>
    </select><br><br>

    <button onclick="createSite()">Create</button>
  `;
}

function openExplorer(siteName) {
  currentSite = siteName;
  currentPath = "";
  loadFiles();
}

function showUpload() {
  document.getElementById("content").innerHTML += `
    <input type="file" id="file">
    <button onclick="uploadFile()">Upload</button>
  `;
}

function downloadFile(name) {
  window.open(`${API}/sites/${currentSite}/download?path=${currentPath}/${name}`);
}

function enterFolder(name) {
  currentPath = currentPath ? `${currentPath}/${name}` : name;
  loadFiles();
}

function goBack() {
  const parts = currentPath.split('/');
  parts.pop();
  currentPath = parts.join('/');
  loadFiles();
}

async function changePHP(siteName) {
  const version = prompt("Enter PHP version (7.4, 8.0, 8.2):");

  await fetch(`${API}/sites/${siteName}/php?version=${version}`, {
    method: "PUT"
  });

  alert("PHP version updated");
  loadSites();
}

async function loadSites() {
  const res = await fetch(`${API}/sites`);
  const sites = await res.json();

  let html = `
    <h2>Sites</h2>
    <table>
      <tr>
        <th>Domain</th>
        <th>Path</th>
        <th>Status</th>
        <th>PHP Version</th>
        <th>Files</th>
        <th>CGI</th>
        <th>SFTP</th>
        <th>SSL</th>
      </tr>
  `;

  sites.forEach(site => {
    html += `
      <tr>
        <td>${site.domain}</td>
        <td>${site.path}</td>
        <td>${site.status}</td>
        <td>${site.php_version}</td>
        <td><button onclick="openExplorer('${site.name}')">Files</button></td>
        <td><button onclick="changePHP('${site.name}')">Change PHP</button></td>
        <td><button onclick="createSFTP('${site.name}')">Enable SFTP</button></td>
        <td><button onclick="enableSSL('${site.name}')">Enable SSL</button></td>
      </tr>
    `;
  });

  html += `</table>`;

  document.getElementById("content").innerHTML = html;
}

async function enableSSL(siteName) {
  await fetch(`${API}/sites/${siteName}/ssl`, {
    method: "POST"
  });

  alert("SSL enabled");
}

async function createSite() {
  const domain = document.getElementById("domain").value;
  const name = document.getElementById("name").value;
  const php_version = document.getElementById("php_version").value;

  await fetch(`${API}/sites`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      domain: domain,
      site_name: name,
      php_version: php_version   // ✅ added
    })
  });

  alert("Site created");
  loadSites();
}

async function loadFiles() {
  const res = await fetch(`${API}/sites/${currentSite}/files?path=${currentPath}`);
  const files = await res.json();

  let html = `<h2>Files: ${currentSite}/${currentPath}</h2>`;

  html += `<button onclick="goBack()">← Back</button>`;
  html += `<button onclick="showUpload()">Upload</button>`;
  html += `<button onclick="createFolder()">New Folder</button>`;

  html += `<table>
    <tr><th>Name</th><th>Type</th><th>Action</th></tr>`;

  files.forEach(f => {
    html += `
      <tr>
        <td onclick="${f.is_dir ? `enterFolder('${f.name}')` : ''}">
          ${f.name}
        </td>
        <td>${f.is_dir ? 'Folder' : 'File'}</td>
        <td>
          ${!f.is_dir ? `<button onclick="downloadFile('${f.name}')">Download</button>` : ''}
          <button onclick="deleteFile('${f.name}')">Delete</button>
        </td>
      </tr>
    `;
  });

  html += `</table>`;

  document.getElementById("content").innerHTML = html;
}

async function uploadFile() {
  const file = document.getElementById("file").files[0];

  const formData = new FormData();
  formData.append("file", file);

  await fetch(`${API}/sites/${currentSite}/upload?path=${currentPath}`, {
    method: "POST",
    body: formData
  });

  loadFiles();
}

async function deleteFile(name) {
  await fetch(`${API}/sites/${currentSite}/delete?path=${currentPath}/${name}`, {
    method: "DELETE"
  });

  loadFiles();
}

async function createFolder() {
  const name = prompt("Folder name:");

  await fetch(`${API}/sites/${currentSite}/mkdir`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      path: currentPath,
      name: name
    })
  });

  loadFiles();
}

async function createSFTP(siteName) {
  const password = prompt("Enter SFTP password:");

  await fetch(`${API}/sites/${siteName}/sftp`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ password })
  });

  alert("SFTP enabled");
}