  function when(iso) { try { return new Date(iso).toLocaleString("en-AU", { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }); } catch (e) { return iso; } }
  function renderStatus(dirty) {
    var st = document.getElementById("status"), note = document.getElementById("statusNote");
    st.className = "status";
    if (!db) { st.textContent = "Showing recommended settings"; note.textContent = "Saved settings could not be loaded in this view."; return; }
    if (!saved) { st.textContent = "Loading settings"; note.textContent = ""; return; }
    var rev = saved.rev || 0, applied = status && status.appliedRev || 0;
    if (dirty) { st.classList.add("dirty"); st.textContent = "Changes not saved"; }
    else if (status && status.result === "failed" && status.appliedRev === rev) { st.classList.add("pending"); st.textContent = "Saved, not live yet"; }
    else if (applied >= rev) { st.classList.add("live"); st.textContent = "Live on the site"; }
    else { st.classList.add("pending"); st.textContent = "Saved, updating the site"; }
    var bits = [];
    if (saved.savedAt) bits.push("Last saved " + when(saved.savedAt) + ".");
    if (status && status.appliedAt && applied >= rev) bits.push("Went live " + when(status.appliedAt) + ".");
    else if (status && status.result === "failed" && status.message) bits.push(status.message);
    else if (applied < rev) bits.push(saved.firing === "queued" ? "Usually live within 5 minutes." : "Goes live with tonight’s 3am update.");
    if (!canEdit) bits.push("You can view these settings. Ask Ben to change them.");
    note.textContent = bits.join(" ");
  }
