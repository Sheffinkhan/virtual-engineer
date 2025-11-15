function addTask() {
    const input = document.getElementById('taskInput');
    const taskText = input.value.trim();
    if (taskText === '') return;

    const taskList = document.getElementById('taskList');
    const li = document.createElement('li');
    li.textContent = taskText;
    taskList.appendChild(li);
    input.value = ''; // Clear input
}
2. Modify the `addTask` function to include the `showLoading` function and remove the loading message after adding the task:
