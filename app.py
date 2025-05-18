from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import json
import google.generativeai as genai
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
# Initialize Google Gemini
genai.configure(api_key="AIzaSyC7AehgiyBc2pAIKZxv7n3YYSvX7I7geD8")
model = genai.GenerativeModel('gemini-2.0-flash')

#Secret key for session management
app.secret_key = 'your-super-secret-key-here'  

# Fake user data with tasks and scores
users = {
    "admin": {
        "password": "password123",
        "tasks": [],
        "scores": [],
        "completed_tasks": set()  # Track completed tasks
    },
    "admin2": {
        "password": "mypassword",
        "tasks": [],
        "scores": [],
        "completed_tasks": set()
    },
    "admin3": {
        "password": "321password",
        "tasks": [],
        "scores": [],
        "completed_tasks": set()
    }
}

def add_task_to_user(username, task_data):
    if username in users:
        task_id = len(users[username]["tasks"])
        task = {
            "id": task_id,
            "name": task_data["task_name"],
            "due_date": task_data["due_date"],
            "topic": task_data["topic"],
            "criteria": task_data["criteria"],
            "details": task_data["details"],
            "plan": task_data["plan"],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "score": 0,
            "completed_subtasks": set()  # Track completed subtasks
        }
        users[username]["tasks"].append(task)
        return task_id
    return None

def get_user_tasks(username):
    if username in users:
        return users[username]["tasks"]
    return []

def format_promt(task_name, due_date, topic, criteria, details):
    #Get cureent date
    current_date = datetime.now().strftime("%Y-%m-%d")
    return f"""Please help me break down this task into detailed daily subtasks:

Task Name: {task_name}
Due Date: {due_date}
Topic/Category: {topic}
Success Criteria: {criteria}
Additional Details: {details}

Please break down the task into daily steps, focusing on:
1. Small, manageable actions
2. Continuous progress
3. Clear, actionable steps
4. Logical sequence of activities

IMPORTANT DATE HANDLING:
- The plan should start from the current date ({current_date})
- The plan should end on or before the due date ({due_date})
- If the due date is very close to the current date, focus on essential steps only
- If the due date is far in the future, break down the task into more detailed steps
- Each day in the plan should be a valid calendar date between {current_date} and {due_date}

For each step, indicate its type using one of these prefixes:
[RESEARCH] - For research and learning tasks
[CREATE] - For creation and development tasks
[REVIEW] - For review and feedback tasks
[PRACTICE] - For practice and implementation tasks
[PLAN] - For planning and organization tasks

IMPORTANT FORMATTING RULES:
1. Start each day with "Day X:" on its own line
2. List steps as numbered items (1., 2., 3., etc.)
3. Each step should be on its own line
4. Include any notes or tips after the steps for that day
5. Make sure to complete all days and steps
6. Do not leave any steps or days incomplete
7. Ensure the total number of days fits within the available time

Example format:
Day 1:
1. [RESEARCH] Research key concepts and fundamentals
2. [PLAN] Create initial outline and structure
3. [CREATE] Gather reference materials
Note: Focus on understanding the core requirements

Day 2:
1. [CREATE] Draft introduction and thesis statement
2. [PRACTICE] Develop main arguments with examples
3. [REVIEW] Check alignment with reference materials
Tip: Use the reference materials from Day 1

Please provide the complete plan in this exact format, ensuring all days and steps are fully listed. Do not cut off or leave any steps incomplete. The plan should be realistic given the time available between {current_date} and {due_date}."""

@app.route('/')
def home():
    if 'username' in session:
        tasks = get_user_tasks(session['username'])
        return f"""
        <div style='font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px;'>
            <h1>Welcome, {session['username']}!</h1>
            <div style='margin: 20px 0;'>
                <a href='/plan' style='text-decoration: none; background: #3498db; color: white; padding: 10px 20px; border-radius: 5px;'>Create New Task Plan</a>
                <a href='/leaderboard' style='text-decoration: none; background: #4361ee; color: white; padding: 10px 20px; border-radius: 5px; margin-left: 10px;'>Leaderboard</a>
                <a href='/logout' style='text-decoration: none; background: #e74c3c; color: white; padding: 10px 20px; border-radius: 5px; margin-left: 10px;'>Logout</a>
            </div>
            <div style='margin-top: 30px;'>
                <h2>Your Tasks ({len(tasks)})</h2>
                {''.join([
                    f"<div style='background: white; padding: 15px; margin: 10px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>"
                    f"<h3>{task['name']}</h3>"
                    f"<p>Due: {task['due_date']}</p>"
                    f"<p>Topic: {task['topic']}</p>"
                    f"<a href='/task/{task['id']}' style='color: #3498db;'>View Plan</a>"
                    f"</div>"
                    for task in tasks
                ])}
            </div>
        </div>
        """
    return "You are not logged in. <a href='/login'>Login here</a>"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]["password"] == password:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/plan', methods=['GET', 'POST'])
def plan():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        task_data = {
            "task_name": request.form['task_name'],
            "due_date": request.form['due_date'],
            "topic": request.form['topic'],
            "criteria": request.form['criteria'],
            "details": request.form['details']
        }

        prompt = format_promt(
            task_data["task_name"],
            task_data["due_date"],
            task_data["topic"],
            task_data["criteria"],
            task_data["details"]
        )
        response = model.generate_content(prompt)
        
        task_data["plan"] = response.text if response and response.text else "No response from AI."
        task_id = add_task_to_user(session['username'], task_data)

        return f"""
        <div class="result-card">
            <h2 style='color: var(--text-color); margin-bottom: 1.5rem;'>Your Personalized Study Plan</h2>
            
            <div style='background: var(--bg-color); padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem;'>
                <p style='margin-bottom: 0.5rem'><strong>Subject:</strong> {task_data["task_name"]}</p>
                <p style='margin-bottom: 0.5rem'><strong>Due Date:</strong> {task_data["due_date"]}</p>
                <p style='margin-bottom: 0.5rem'><strong>Topic:</strong> {task_data["topic"]}</p>
            </div>

            <div style='white-space: pre-wrap; background: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #e9ecef; margin-bottom: 1.5rem; line-height: 1.6;'>
                {task_data["plan"]}
            </div>

            <div style='display: flex; gap: 1rem; margin-top: 1.5rem;'>
                <a href='/plan' style='text-decoration: none; background: var(--primary-color); color: white; padding: 0.8rem 1.5rem; border-radius: 6px; flex: 1; text-align: center; transition: all 0.3s ease;'>Create New Plan</a>
                <a href='/' style='text-decoration: none; background: var(--text-color); color: white; padding: 0.8rem 1.5rem; border-radius: 6px; flex: 1; text-align: center; transition: all 0.3s ease;'>Back to Dashboard</a>
            </div>
        </div>
        """

    return render_template('plan.html')

@app.route('/task/<int:task_id>')
def view_task(task_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    tasks = get_user_tasks(session['username'])
    if task_id < len(tasks):
        task = tasks[task_id]
        return f"""
        <div style='font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);'>
            <h2 style='color: #2c3e50;'>{task['name']}</h2>
            <div style='margin: 20px 0;'>
                <p><strong>Due Date:</strong> {task['due_date']}</p>
                <p><strong>Topic:</strong> {task['topic']}</p>
                <p><strong>Success Criteria:</strong> {task['criteria']}</p>
                <p><strong>Created:</strong> {task['created_at']}</p>
            </div>
            <div style='white-space: pre-wrap; background: #f8f9fa; padding: 20px; border-radius: 5px;'>
                {task['plan']}
            </div>
            <a href='/' style='display: block; margin-top: 20px; color: #3498db; text-decoration: none;'>Back to Home</a>
        </div>
        """
    return redirect(url_for('home'))

# API endpoints for scores
@app.route("/add_score", methods=["POST"])
def add_score():
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    username = session['username']
    users[username]["scores"].append({
        "score": data["score"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    return jsonify({"message": "Score added!"})

@app.route("/user_scores", methods=["GET"])
def user_scores():
    username = request.args.get("username")
    if username in users:
        return jsonify(sorted(users[username]["scores"], key=lambda x: x["score"], reverse=True))
    return jsonify([])

@app.route('/leaderboard')
def leaderboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('leaderboard.html')

@app.route('/leaderboard_data')
def leaderboard_data():
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    # Calculate statistics
    total_users = len(users)
    total_plans = sum(len(user["tasks"]) for user in users.values())
    all_scores = [score["score"] for user in users.values() for score in user["scores"]]
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    highest_score = max(all_scores) if all_scores else 0

    # Prepare leaderboard data
    leaderboard_data = []
    for username, user_data in users.items():
        total_score = sum(score["score"] for score in user_data["scores"])
        leaderboard_data.append({
            "username": username,
            "plans_created": len(user_data["tasks"]),
            "score": total_score
        })
    
    # Sort leaderboard by score
    leaderboard_data.sort(key=lambda x: x["score"], reverse=True)

    # Get activity data (last 7 days)
    today = datetime.now()
    activity_labels = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    activity_values = [0] * 7  # Placeholder for actual values

    return jsonify({
        "stats": {
            "total_users": total_users,
            "total_plans": total_plans,
            "avg_score": round(avg_score, 1),
            "highest_score": highest_score
        },
        "leaderboard": leaderboard_data,
        "activity_data": {
            "labels": activity_labels,
            "values": activity_values
        }
    })

@app.route('/update_progress', methods=['POST'])
def update_progress():
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    username = session['username']
    task_id = data.get('task_id')
    completed = data.get('completed')
    
    if task_id is None or completed is None:
        return jsonify({"error": "Missing task_id or completed status"}), 400
    
    # Update the task completion status
    task_key = f"{task_id}"
    if completed:
        users[username]["completed_tasks"].add(task_key)
        # Add points for completing a task
        users[username]["scores"].append({
            "score": 10,  # Points for completing a task
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "task_completion"
        })
    else:
        users[username]["completed_tasks"].discard(task_key)
        # Optionally remove points for uncompleting a task
        users[username]["scores"].append({
            "score": -10,  # Remove points for uncompleting a task
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "task_uncompletion"
        })
    
    return jsonify({
        "success": True,
        "message": "Progress updated successfully",
        "completed": completed
    })

if __name__ == '__main__':
    # Run on localhost only for security
    app.run(debug=True, port=8081)

