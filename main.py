"""Launch the desktop application, or explicitly verify a standalone build."""
import sys

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        import os
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from cropper.smoke import run
        raise SystemExit(run(sys.argv[2]))
    else:
        from cropper.gui import run
        raise SystemExit(run())
