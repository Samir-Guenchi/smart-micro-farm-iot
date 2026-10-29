# Phase 0 Firmware CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task by task.

**Goal:** Build every PlatformIO project under `firmware/*`, prepare example credentials, pass with an empty firmware directory, and show workflow status in the README.

**Architecture:** A single GitHub Actions workflow discovers `platformio.ini` files one directory below `firmware/`, copies each example secrets header to its ignored build-time path, and compiles the project. An empty project list exits successfully.

**Tech Stack:** GitHub Actions, Python, PlatformIO Core, Bash on `ubuntu-latest`.

**Spec:** `docs/superpowers/specs/2026-10-29-phase-0-assigned-issues-design.md`

## Global Constraints

- Discover all projects under `firmware/*/` by presence of `platformio.ini`.
- Before each build, copy `include/secrets.example.h` to `include/secrets.h`.
- Run `pio run` for each discovered project.
- An empty or missing `firmware/` directory must exit successfully.
- The root `.gitignore` excludes `.pio` build output and every real `include/secrets.h`.
- Add a status badge for the new firmware workflow to the README.

---

## File Structure

- `.github/workflows/firmware.yml`: workflow triggers, PlatformIO setup, project discovery, example-secret preparation, and builds.
- `.gitignore`: local PlatformIO outputs and secrets exclusion.
- `README.md`: badge linked to the workflow runs page.

## Task 1: Ignore Generated Files and Credentials

**Files:**
- Create: `.gitignore`

- [ ] Add `**/.pio/` to ignore PlatformIO build directories.
- [ ] Add `**/include/secrets.h` to ignore real node credentials while keeping committed `secrets.example.h` files visible.
- [ ] Add `__pycache__/` and `.DS_Store` to prevent unrelated local tooling noise.
- [ ] Confirm `git status --short` does not show generated PlatformIO files or any future local `include/secrets.h` after builds.

## Task 2: Add the Firmware Build Workflow

**Files:**
- Create: `.github/workflows/firmware.yml`

- [ ] Trigger on pushes and pull requests affecting `firmware/**`, `.github/workflows/firmware.yml`, `.gitignore`, or `README.md`; include `workflow_dispatch` for manual runs.
- [ ] Check out the repository and discover `firmware/*/platformio.ini` paths in sorted order before installing PlatformIO. If `firmware/` is absent or no paths exist, print `No PlatformIO projects found; nothing to build.` and exit 0.
- [ ] When at least one project exists, install Python 3 and install PlatformIO Core with `python -m pip install platformio`.
- [ ] For each discovered project, require `include/secrets.example.h`, copy it to `include/secrets.h`, change into the project directory, and run `pio run`.
- [ ] Fail the workflow if the example header is missing or any project build returns a non-zero exit status.
- [ ] Keep the loop sequential so logs clearly identify the project that failed and credentials never come from repository secrets.

## Task 3: Add the README Badge

**Files:**
- Modify: `README.md`

- [ ] Add a Markdown badge near the current status section using workflow path `actions/workflows/firmware.yml/badge.svg` and link it to the repository's firmware workflow page.
- [ ] Keep the existing README introduction, brand assets, and project overview unchanged.

## CI Build Command

The workflow's project-level compile command is `pio run`. It runs once per discovered PlatformIO project and is the build acceptance check for issues #4, #5, #6, and #11.
