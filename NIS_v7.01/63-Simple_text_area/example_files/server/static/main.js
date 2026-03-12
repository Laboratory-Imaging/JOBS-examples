// Text area used to display and edit the task value.
const editor = document.getElementById("editor");

// Button for saving the edited value to the server.
const saveBtn = document.getElementById("saveBtn");

// Button for loading the current value from the server.
const loadBtn = document.getElementById("loadBtn");

// Area used to display status messages such as load/save results.
const status = document.getElementById("status");

// Display a status message below the editor.
// Errors are shown in red, successful operations in green.
function showStatus(msg, isError = false) {
    status.style.color = isError ? "red" : "green";
    status.textContent = msg;
}

// Build the value endpoint URL from the current page URL.
// For example: /{task}/external-form/ui -> /{task}/external-form/value
function valueUrl() {
    const url = new URL(window.location.href);
    url.pathname = url.pathname.replace(/\/ui$/, "/value");
    return url.toString();
}

// Load the current task value from the server and display it in the editor.
async function loadValue() {
    try {
        const resp = await fetch(valueUrl());
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        const data = await resp.json();
        if (typeof data.value === "object") {
            editor.value = JSON.stringify(data.value, null, 2);
        }
        else {
            editor.value = data.value ?? "";
        }
        showStatus("Loaded");
    } catch (err) {
        showStatus("Failed to load value", true);
    }
}

// Save the edited value back to the server.
// If the text contains valid JSON, send it as a parsed object;
// otherwise send it as a plain string.
async function saveValue() {
    try {
        let value = editor.value;
        try {
            value = JSON.parse(value);
        } catch {
        }
        const resp = await fetch(valueUrl(), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value })
        });
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        showStatus("Saved");
    } catch (err) {
        showStatus("Failed to save value", true);
    }
}

// Save the current editor value when the Save button is clicked.
saveBtn.addEventListener("click", saveValue);

// Reload the current value from the server when the Load button is clicked.
loadBtn.addEventListener("click", loadValue);

// Load the initial value when the page is opened.
window.addEventListener("DOMContentLoaded", loadValue);