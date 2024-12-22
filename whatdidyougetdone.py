#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "PyGithub>=2.1.1",
#   "click>=8.1.7",
# ]
# [tool.uv]
# exclude-newer = "2024-01-01T00:00:00Z"
# ///
#
# What Did You Get Done? - Activity report generator
# Usage:
#   ./whatdidyougetdone.py report <username>
#   ./whatdidyougetdone.py team <username1> <username2> ...

import click
from datetime import datetime, timedelta, timezone
import os
from typing import Optional
import webbrowser
from github import Github

def setup_github():
    """Ensure GitHub token is available."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Please set GITHUB_TOKEN environment variable")
        print("You can create one at: https://github.com/settings/tokens")
        print("Required scopes: repo, read:user")
        exit(1)

def get_user_activity(username: str, days: int = 7):
    """Get GitHub activity for a user over the last N days."""
    g = Github(os.getenv("GITHUB_TOKEN"))
    user = g.get_user(username)
    
    # Calculate date range (in UTC)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Get all events
    activities = []
    for event in user.get_events():
        if event.created_at < start_date:
            break
            
        # Format based on event type
        if event.type == "PushEvent":
            for commit in event.payload["commits"]:
                activities.append({
                    "type": "commit",
                    "repo": event.repo.name,
                    "message": commit["message"],
                    "date": event.created_at
                })
        elif event.type == "PullRequestEvent":
            activities.append({
                "type": "pr",
                "repo": event.repo.name,
                "title": event.payload["pull_request"]["title"],
                "state": event.payload["pull_request"]["state"],
                "date": event.created_at
            })
        # Add more event types as needed
    
    return activities

def generate_report(username: str, days: int = 7):
    """Generate a markdown report of user activity."""
    activities = get_user_activity(username, days)
    
    # Group by repo
    repos = {}
    for activity in activities:
        repo = activity["repo"]
        if repo not in repos:
            repos[repo] = []
        repos[repo].append(activity)
    
    # Generate markdown
    report = f"# What did {username} get done?\n\n"
    report += f"Activity report for the last {days} days:\n\n"
    
    for repo, acts in repos.items():
        report += f"## {repo}\n\n"
        for act in sorted(acts, key=lambda x: x["date"], reverse=True):
            if act["type"] == "commit":
                report += f"- 💻 {act['message']}\n"
            elif act["type"] == "pr":
                report += f"- 🔀 {act['title']} ({act['state']})\n"
    
    return report

def save_report(username: str, report: str):
    """Save report to file."""
    filename = f"reports/{username}-{datetime.now().strftime('%Y-%m-%d')}.md"
    os.makedirs("reports", exist_ok=True)
    with open(filename, "w") as f:
        f.write(report)
    return filename

@click.group()
def cli():
    """What did you get done? - Activity report generator"""
    pass

@cli.command()
@click.argument("username")
@click.option("--days", default=7, help="Number of days to look back")
@click.option("--output", help="Output file (default: reports/<username>-<date>.md)")
def report(username: str, days: int, output: Optional[str]):
    """Generate activity report for a GitHub user"""
    setup_github()
    
    # Generate report
    activities = get_user_activity(username, days)
    report_text = generate_report(username, days)
    
    # Save report
    if output:
        filename = output
    else:
        filename = save_report(username, report_text)
    
    print(f"Report saved to: {filename}")
    
    # Preview in browser
    if click.confirm("Open in browser?"):
        webbrowser.open(f"file://{os.path.abspath(filename)}")

@cli.command()
@click.argument("usernames", nargs=-1)
@click.option("--days", default=7, help="Number of days to look back")
def team(usernames: tuple[str], days: int):
    """Generate team activity report"""
    setup_github()
    
    # Generate combined report
    report = f"# Team Activity Report\n\n"
    report += f"Activity for the last {days} days\n\n"
    
    for username in usernames:
        activities = get_user_activity(username, days)
        report += f"## {username}\n\n"
        
        # Count activities
        commit_count = sum(1 for a in activities if a["type"] == "commit")
        pr_count = sum(1 for a in activities if a["type"] == "pr")
        
        report += f"- 💻 {commit_count} commits\n"
        report += f"- 🔀 {pr_count} pull requests\n\n"
        
        # Add details
        for activity in sorted(activities, key=lambda x: x["date"], reverse=True):
            if activity["type"] == "commit":
                report += f"- [{activity['repo']}] {activity['message']}\n"
            elif activity["type"] == "pr":
                report += f"- [{activity['repo']}] {activity['title']} ({activity['state']})\n"
        report += "\n"
    
    # Save report
    filename = f"reports/team-{datetime.now().strftime('%Y-%m-%d')}.md"
    os.makedirs("reports", exist_ok=True)
    with open(filename, "w") as f:
        f.write(report)
    
    print(f"Team report saved to: {filename}")
    
    # Preview in browser
    if click.confirm("Open in browser?"):
        webbrowser.open(f"file://{os.path.abspath(filename)}")

if __name__ == "__main__":
    cli()
