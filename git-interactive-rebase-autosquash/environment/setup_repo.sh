#!/bin/bash
set -e

# Configure git
git config --global user.email "test@example.com"
git config --global user.name "Test User"
git config --global init.defaultBranch main

# Create repo
mkdir -p /app/repo
cd /app/repo
git init

# Initial commit on main
echo "# Project" > README.md
git add README.md
git commit -m "Initial commit"

# Create feature branch
git checkout -b feature/user-dashboard

# Commit 1: Add user dashboard layout
cat > dashboard.html << 'HTMLEOF'
<!DOCTYPE html>
<html>
<head><title>Dashboard</title></head>
<body>
<div id="dashboard">
</div>
</body>
</html>
HTMLEOF
git add dashboard.html
git commit -m "Add user dashboard layout"

# Commit 2: WIP: experimenting with styles
cat > styles.css << 'CSSEOF'
body { margin: 0; }
CSSEOF
git add styles.css
git commit -m "WIP: experimenting with styles"

# Commit 3: Add sidebar navigation
cat > sidebar.html << 'HTMLEOF'
<nav id="sidebar">
</nav>
HTMLEOF
git add sidebar.html
git commit -m "Add sidebar navigation"

# Commit 4: fixup! Add user dashboard layout
cat > dashboard.html << 'HTMLEOF'
<!DOCTYPE html>
<html>
<head><title>Dashboard</title></head>
<body>
<div id="dashboard">
<header>User Dashboard</header>
</div>
</body>
</html>
HTMLEOF
git add dashboard.html
git commit -m "fixup! Add user dashboard layout"

# Commit 5: Add user profile component
cat > profile.js << 'JSEOF'
function renderProfile() {
    const container = document.getElementById('profile');
    container.innerHTML = '<h2>User Profile</h2>';
}
JSEOF
git add profile.js
git commit -m "Add user profile component"

# Commit 6: WIP: debugging profile
cat > profile.js << 'JSEOF'
function renderProfile() {
    console.log("debug");
    const container = document.getElementById('profile');
    container.innerHTML = '<h2>User Profile</h2>';
}
JSEOF
git add profile.js
git commit -m "WIP: debugging profile"

# Commit 7: fixup! Add sidebar navigation
cat > sidebar.html << 'HTMLEOF'
<nav id="sidebar">
<ul>
<li>Home</li>
<li>Profile</li>
<li>Settings</li>
</ul>
</nav>
HTMLEOF
git add sidebar.html
git commit -m "fixup! Add sidebar navigation"

# Commit 8: Add dashboard API integration
cat > api.js << 'JSEOF'
function fetchDashboardData() {
    return fetch('/api/dashboard')
        .then(response => response.json());
}
JSEOF
git add api.js
git commit -m "Add dashboard API integration"

# Commit 9: squash! Add user profile component
cat > profile.js << 'JSEOF'
function renderProfile() {
    console.log("debug");
    const container = document.getElementById('profile');
    container.innerHTML = '<h2>User Profile</h2>';
}

function updateProfile() {
    const data = { name: 'User', email: 'user@example.com' };
    return fetch('/api/profile', { method: 'POST', body: JSON.stringify(data) });
}
JSEOF
git add profile.js
git commit -m "squash! Add user profile component"

# Commit 10: fixup! Add dashboard API integration
cat > api.js << 'JSEOF'
function fetchDashboardData() {
    try {
        return fetch('/api/dashboard')
            .then(response => response.json());
    } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
        return Promise.reject(error);
    }
}
JSEOF
git add api.js
git commit -m "fixup! Add dashboard API integration"

# Commit 11: WIP: temp changes
echo "temporary" > temp.txt
git add temp.txt
git commit -m "WIP: temp changes"

# Commit 12: Add unit tests for dashboard
cat > tests.js << 'JSEOF'
function testDashboard() {
    const dashboard = document.getElementById('dashboard');
    console.assert(dashboard !== null, 'Dashboard should exist');
}
JSEOF
git add tests.js
git commit -m "Add unit tests for dashboard"

# Commit 13: fixup! Add user dashboard layout
cat > dashboard.html << 'HTMLEOF'
<!DOCTYPE html>
<html>
<head><title>Dashboard</title></head>
<body>
<div id="dashboard">
<header>User Dashboard</header>
<footer>Dashboard Footer</footer>
</div>
</body>
</html>
HTMLEOF
git add dashboard.html
git commit -m "fixup! Add user dashboard layout"

# Commit 14: Add documentation
cat > README_FEATURE.md << 'MDEOF'
# User Dashboard Feature

This feature provides a comprehensive user dashboard with sidebar navigation,
user profile management, API integration, and unit tests.
MDEOF
git add README_FEATURE.md
git commit -m "Add documentation"

# Commit 15: squash! Add unit tests for dashboard
cat > tests.js << 'JSEOF'
function testDashboard() {
    const dashboard = document.getElementById('dashboard');
    console.assert(dashboard !== null, 'Dashboard should exist');
}

function testSidebar() {
    const sidebar = document.getElementById('sidebar');
    console.assert(sidebar !== null, 'Sidebar should exist');
}
JSEOF
git add tests.js
git commit -m "squash! Add unit tests for dashboard"

echo "Repository setup complete with 15 commits on feature/user-dashboard"
git log --oneline
