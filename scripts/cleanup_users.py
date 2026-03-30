import os
import django
import sys
from collections import defaultdict

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import transaction
from registrations.models import Registration
from teams.models import Team, TeamMember
from contests.models import Contest

def cleanup_duplicate_usernames():
    print("--- Starting Case-Insensitive Username Cleanup ---")
    
    # 1. Group users by lowercase username
    users_by_lower = defaultdict(list)
    for u in User.objects.all():
        users_by_lower[u.username.lower()].append(u)
    
    total_merged = 0
    total_normalized = 0
    
    with transaction.atomic():
        for lower_name, user_list in users_by_lower.items():
            if len(user_list) > 1:
                # Pick Master: 1. Staff users, 2. Already lowercase, 3. Oldest ID
                master = next((u for u in user_list if u.is_staff), None)
                if not master:
                    master = next((u for u in user_list if u.username == lower_name), user_list[0])
                
                duplicates = [u for u in user_list if u != master]
                print(f"[GROUP] {lower_name}: Master is '{master.username}' (ID: {master.id})")
                
                for dupe in duplicates:
                    print(f"  -> Merging duplicate '{dupe.username}' (ID: {dupe.id})")
                    
                    # A. Reassign Registrations (Safely)
                    for reg in Registration.objects.filter(user=dupe):
                        if not Registration.objects.filter(user=master, contest=reg.contest).exists():
                            reg.user = master
                            reg.save()
                        else:
                            reg.delete() # Master already registered
                    
                    # B. Reassign Team Memberships (Safely)
                    for tm in TeamMember.objects.filter(user=dupe):
                        if not TeamMember.objects.filter(user=master, team=tm.team).exists():
                            tm.user = master
                            tm.save()
                        else:
                            tm.delete() # Master already in team
                            
                    # C. Reassign Team Leadership
                    Team.objects.filter(leader=dupe).update(leader=master)
                    
                    # D. Reassign Contest Organizers
                    for contest in Contest.objects.filter(organizers=dupe):
                        contest.organizers.add(master)
                        contest.organizers.remove(dupe)
                    
                    # E. Delete the Duplicate
                    dupe.delete()
                    total_merged += 1
                
                # F. Normalize Master to lowercase
                if master.username != lower_name:
                    master.username = lower_name
                    master.save()
                    total_normalized += 1
            else:
                # Single user, just normalize to lowercase if not already
                u = user_list[0]
                if u.username != lower_name:
                    print(f"[NORMALIZE] '{u.username}' -> '{lower_name}'")
                    u.username = lower_name
                    u.save()
                    total_normalized += 1
                    
    print(f"--- Cleanup Finished ---")
    print(f"Total Users Merged: {total_merged}")
    print(f"Total Users Normalized to Lowercase: {total_normalized}")

if __name__ == "__main__":
    cleanup_duplicate_usernames()
