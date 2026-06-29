#!/bin/bash
cd ~/Documents/healthflow
echo ""
echo "Clearing cached GitHub credentials..."
printf "protocol=https\nhost=github.com\n" | git credential reject 2>/dev/null || true
echo ""
echo "Pushing to https://github.com/janhavijadhav/healthflow ..."
echo "When prompted, enter your GitHub username and paste your token as the password."
echo ""
git -c credential.helper= push -u origin main
echo ""
echo "Done! Press Enter to close."
read
