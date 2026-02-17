# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## GitHub Automation (Non-interactive)

- GitHub HTTPS password auth is deprecated. Do not use account password for `git push`.
- Use one of:
  - Existing `gh auth` session
  - PAT token
  - SSH key auth
- Never embed raw email/password in remote URLs.

### Push Playbook

1. Detect current branch:
   - `git branch --show-current`
2. If repo has no commits, create first commit before pushing.
3. Ensure remote exists and is correct:
   - `git remote -v`
4. Push current branch safely:
   - `git push -u origin HEAD`
   - Avoid hardcoding `main` unless it exists.
5. Verify:
   - `git ls-remote --heads origin`

### Non-interactive Rule

- Avoid commands that require TTY interaction inside tool calls:
  - `sudo` password prompts
  - `gpg` commands that open `/dev/tty`
  - browser/device login prompts
- Prefer user-space installs and non-interactive flags (`--batch`, `--yes`) where supported.
- If non-interactive path is impossible, ask for the smallest required credential/input and continue immediately.
