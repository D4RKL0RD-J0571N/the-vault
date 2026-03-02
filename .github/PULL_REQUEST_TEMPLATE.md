## Pull Request Template

### Description
Brief description of changes made in this PR.

### Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactor (non-breaking change that improves code quality)
- [ ] Performance improvement
- [ ] Other (please describe)

### Testing
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Coverage remains at 95%+
- [ ] Manual testing completed

### Checklist
- [ ] Code follows project conventions in AGENTS.md
- [ ] Self-review of code completed
- [ ] Documentation updated if needed
- [ ] CHANGELOG.md updated with changes
- [ ] Commits follow conventional format
- [ ] PR targets correct branch (`dev` for features, `main` for hotfixes)

### Architecture Compliance
- [ ] Parser layer does not call Ollama
- [ ] All file system access through crawler module
- [ ] FastAPI routes remain thin
- [ ] No direct file access from frontend (if applicable)

### Issue Reference
Closes #(issue number)

### Additional Notes
Any additional context or notes about this PR.
