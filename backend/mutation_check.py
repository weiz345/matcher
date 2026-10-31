"""Focused hand-selected mutation checks; never edits working app code or its DB.
Run: python3 backend/mutation_check.py
Each mutant must make a relevant regression test fail. This is not a full mutation score.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
MUTANTS = [
    ('skip conversation membership check', 'database.py',
     "WHERE id=? AND active=1 AND (a=? OR b=?)',(cid,me,me)",
     "WHERE id=? AND active=1',(cid,)",
     'test_nonmember_and_unmatched_access'),
    ('allow messages after unmatch', 'database.py',
     "WHERE id=? AND active=1 AND (a=? OR b=?)",
     "WHERE id=? AND (a=? OR b=?)",
     'test_nonmember_and_unmatched_access'),
    ('ignore block visibility', 'database.py',
     "return me != other and not db.execute('SELECT 1 FROM user_blocks WHERE (blocker=? AND blocked=?) OR (blocker=? AND blocked=?)',(me,other,other,me)).fetchone()",
     "return me != other",
     'test_block_revokes_both_sides'),
    ('accept any login password', 'server.py',
     "if not row or not secrets.compare_digest(digest,row['password_hash']):",
     "if not row:",
     'test_signup_passwords_sessions_and_logout'),
    ('create match without reciprocal like', 'database.py',
     "if db.execute('SELECT 1 FROM user_likes WHERE sender=? AND recipient=?',(target,me)).fetchone():",
     "if True:",
     'test_messages_delivered_and_never_scripted'),
    ('allow deletion of another account photo', 'server.py',
     "DELETE FROM photos WHERE id=? AND user_id=?',(parts[2],me)",
     "DELETE FROM photos WHERE id=?',(parts[2],)",
     'test_photo_profile_ownership_and_restart'),
    ('remove idempotent message insert', 'server.py',
     'INSERT OR IGNORE INTO chat_messages',
     'INSERT INTO chat_messages',
     'test_messages_delivered_and_never_scripted'),
    ('ignore ownership of liked prompt/photo', 'database.py',
     "if not table or not db.execute(f'SELECT 1 FROM {table} WHERE id=? AND user_id=?',(item_id,target)).fetchone():",
     "if not table:",
     'test_like_ownership_and_mutual_match'),
]

def run_case(folder, test):
    return subprocess.run([sys.executable,'-m','unittest','test_server.AccountTests.'+test],
                          cwd=folder,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=40)

def main():
    survivors=[]
    for name,file,old,new,test in MUTANTS:
        with tempfile.TemporaryDirectory(prefix='hinge-mutation-') as temp:
            root=Path(temp)
            shutil.copytree(ROOT/'backend',root/'backend',ignore=shutil.ignore_patterns('__pycache__'))
            (root/'ios').symlink_to(ROOT/'ios',target_is_directory=True)
            baseline=run_case(root/'backend',test)
            if baseline.returncode:
                print(baseline.stdout);raise SystemExit('Baseline failed for '+name)
            path=root/'backend'/file;source=path.read_text()
            assert source.count(old)==1,(name,source.count(old))
            path.write_text(source.replace(old,new,1))
            shutil.rmtree(root/'backend/__pycache__',ignore_errors=True)
            result=run_case(root/'backend',test)
            if result.returncode and ('FAIL:' in result.stdout):
                print('KILLED:',name,flush=True)
            else:
                print('SURVIVED / inconclusive:',name,flush=True)
                print(result.stdout);survivors.append(name)
    print(f'{len(MUTANTS)-len(survivors)}/{len(MUTANTS)} selected mutations killed.')
    if survivors: raise SystemExit(1)

if __name__=='__main__':main()
