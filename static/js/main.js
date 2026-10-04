// Campus Connect Main Interactivity Logic

document.addEventListener('DOMContentLoaded', function () {
  // 1. Dashboard Sidebar Navigation & Tab Switching
  const navItems = document.querySelectorAll('.nav-item[data-tab]');
  const tabPanes = document.querySelectorAll('.tab-pane');

  navItems.forEach(item => {
    item.addEventListener('click', function () {
      const targetTab = this.getAttribute('data-tab');

      // Update active nav link
      navItems.forEach(nav => nav.classList.remove('active'));
      this.classList.add('active');

      // Show target tab pane
      tabPanes.forEach(pane => {
        if (pane.id === targetTab) {
          pane.classList.add('active');
        } else {
          pane.classList.remove('active');
        }
      });
    });
  });

  // 2. Modal Window Controls
  const modalTriggers = document.querySelectorAll('[data-modal-target]');
  const modalCloses = document.querySelectorAll('[data-modal-close]');

  modalTriggers.forEach(trigger => {
    trigger.addEventListener('click', function () {
      const targetModalId = this.getAttribute('data-modal-target');
      const modal = document.getElementById(targetModalId);
      if (modal) {
        modal.classList.add('active');
      }
    });
  });

  modalCloses.forEach(closeBtn => {
    closeBtn.addEventListener('click', function () {
      const modal = this.closest('.modal-backdrop');
      if (modal) {
        modal.classList.remove('active');
      }
    });
  });

  // Close modal when clicking on backdrop
  document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', function (e) {
      if (e.target === this) {
        this.classList.remove('active');
      }
    });
  });

  // 3. Task Completion Checkbox AJAX Toggle
  const taskCheckboxes = document.querySelectorAll('.task-checkbox');
  taskCheckboxes.forEach(cb => {
    cb.addEventListener('change', function () {
      const taskId = this.getAttribute('data-task-id');
      const taskItem = document.getElementById(`task-item-${taskId}`);

      fetch(`/student/task/toggle/${taskId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          if (data.is_completed) {
            taskItem.classList.add('completed');
          } else {
            taskItem.classList.remove('completed');
          }
        }
      })
      .catch(err => console.error('Error toggling task:', err));
    });
  });

  // 4. Auto Dismiss Alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 300);
    }, 5000);
  });
});
