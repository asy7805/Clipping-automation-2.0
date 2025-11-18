# Git Workflow Guide

## Branch Strategy

This project uses a three-tier branch workflow to separate development, testing, and production deployments.

### Branch Structure

```
feature branches → main → production
```

### Branch Purposes

#### 1. **Feature Branches** (e.g., `feature/improvement-name`, `fix/bug-name`)
- **Purpose**: Individual developers work on their own tasks
- **Naming**: Use descriptive names like `feature/add-new-feature` or `fix/resolve-bug`
- **Workflow**:
  - Create from `main`: `git checkout -b feature/your-feature-name main`
  - Make commits and push: `git push origin feature/your-feature-name`
  - Create a Pull Request to merge into `main`

#### 2. **Main Branch** (`main`)
- **Purpose**: Development and revision branch
- **Contains**: Backend code, scripts, API, and core functionality
- **Does NOT contain**: Frontend code (frontend is only in `production`)
- **Workflow**:
  - Merge feature branches here after review
  - Test backend changes here
  - When ready for deployment, merge `main` into `production`

#### 3. **Production Branch** (`production`)
- **Purpose**: Deployment-ready code
- **Contains**: Full stack (backend + frontend)
- **Deployment**: 
  - Vercel automatically deploys from this branch
  - Root directory: `frontend/`
  - Production branch setting in Vercel: `production`
- **Workflow**:
  - Merge `main` into `production` when ready to deploy
  - Only deploy-ready code should be here
  - Frontend changes go directly here or via `main` → `production` merge

## Common Workflows

### Adding a New Feature

1. **Create feature branch from main:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and commit:**
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   git push origin feature/your-feature-name
   ```

3. **Create Pull Request** to merge into `main`

4. **After PR is merged**, when ready to deploy:
   ```bash
   git checkout production
   git pull origin production
   git merge main
   git push origin production
   ```

### Making Frontend Changes

Since frontend code is only in `production`:

1. **Option A: Direct to production** (for frontend-only changes):
   ```bash
   git checkout production
   git checkout -b feature/frontend-change
   # Make changes
   git commit -m "feat: Frontend improvement"
   git push origin feature/frontend-change
   # Create PR to production, or merge directly
   ```

2. **Option B: Via main** (if backend changes are also needed):
   - Make backend changes in a feature branch → merge to `main`
   - Make frontend changes in `production` or merge `main` → `production`

### Deploying to Production

1. **Ensure main is up to date:**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Merge main into production:**
   ```bash
   git checkout production
   git pull origin production
   git merge main
   git push origin production
   ```

3. **Vercel will automatically deploy** from the `production` branch

## Important Notes

- **Main branch does NOT contain frontend code** - it's backend-only
- **Production branch contains the full stack** - frontend + backend
- **Vercel is configured to deploy from `production` branch only**
- **Never force push to `production`** unless absolutely necessary
- **Always test in `main` before merging to `production`**

## Current Configuration

- **Vercel Root Directory**: `frontend`
- **Vercel Production Branch**: `production`
- **Vercel Framework**: Vite
- **Build Command**: `npm install && npm run build`
- **Output Directory**: `dist`

## Troubleshooting

### If main has frontend code (shouldn't happen):
```bash
git checkout main
git reset --hard <commit-before-frontend>
git push origin main --force
```

### If production is missing frontend:
```bash
git checkout production
git merge main  # or cherry-pick specific commits
git push origin production
```

### To check branch status:
```bash
git log --oneline --all --graph | head -20
```

