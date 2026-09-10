#!/usr/bin/env python3
"""Add a package-boundary pause to LibreELEC's existing scheduler."""
import argparse
from pathlib import Path

def patch(source):
 p=source/'scripts/pkgbuilder.py';s=p.read_text()
 marker='    def queueWork(self):\n'
 addition='''
        # Drain active packages before a resumable Actions checkpoint.
        deadline = float(os.environ.get("T95H_BUILD_DEADLINE", "inf"))
        if time.time() >= deadline:
            if self.generator.activeJobCount() != 0:
                return True
            if self.generator.failedJobCount() == 0:
                with open(os.environ["T95H_PAUSE_MARKER"], "w") as marker:
                    marker.write("drained\\n")
                self.checkpoint_paused = True
            return False
'''
 end='    sys.exit(0 if result else 1)'
 if s.count(marker)!=1 or s.count(end)!=1:raise ValueError('LibreELEC scheduler changed; checkpoint adapter needs review')
 s=s.replace(marker,marker+addition).replace(end,'    sys.exit(75 if getattr(builder, "checkpoint_paused", False) else (0 if result else 1))')
 compile(s,str(p),'exec');p.write_text(s)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);patch(p.parse_args().source)
