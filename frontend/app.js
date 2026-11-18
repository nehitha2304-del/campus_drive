const userList = document.querySelector("#user-list");
const memberCount = document.querySelector("#member-count");
const memberStatus = document.querySelector("#member-status");
const directoryLabel = document.querySelector("#directory-label");

function initials(email) {
  return (email || "?").trim().slice(0, 1).toUpperCase();
}

async function loadCommunity() {
  try {
    const response = await fetch("/api/users", { headers: { Accept: "application/json" } });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "The directory is unavailable.");

    const users = Array.isArray(payload.users) ? payload.users : [];
    memberCount.textContent = String(users.length).padStart(2, "0");
    memberStatus.textContent = "From Supabase";
    directoryLabel.textContent = "Live directory";

    if (users.length === 0) {
      userList.innerHTML = '<div class="empty-state">No community members to show yet.</div>';
      return;
    }

    userList.innerHTML = users.slice(0, 6).map((user) => {
      const email = typeof user.email === "string" ? user.email : "Campus member";
      return `<div class="user-item"><span class="user-avatar" aria-hidden="true">${initials(email)}</span><span class="user-email" title="${escapeAttribute(email)}">${escapeHTML(email)}</span></div>`;
    }).join("");
  } catch (error) {
    memberCount.textContent = "—";
    memberStatus.textContent = "Offline";
    directoryLabel.textContent = "Directory unavailable";
    userList.innerHTML = `<div class="error-state">${escapeHTML(error.message)} Check the Supabase environment variables and users table.</div>`;
  }
}

function escapeHTML(value) {
  return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

function escapeAttribute(value) {
  return escapeHTML(value);
}

loadCommunity();
