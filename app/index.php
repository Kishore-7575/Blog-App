<?php
// Path to your Python script
$pythonScriptPath = 'E:/downloads/flask-blog-app-master/flask-blog-app-master/app/app.py';

// Command to run the Python script
$command = "python $pythonScriptPath 2>&1";

// Execute the command
$output = shell_exec($command);

// Display output (optional)
echo "<pre>$output</pre>";
?>
