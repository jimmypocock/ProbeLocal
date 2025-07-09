# Visual Testing Checklist for Greg AI Playground

This checklist should be manually verified before each release or major change.

## Pre-Test Setup

- [ ] Ensure all services are running: `make run`
- [ ] Clear browser cache and cookies
- [ ] Test in multiple browsers: Chrome, Firefox, Safari
- [ ] Test in both light and dark modes (if applicable)

## 1. Initial Load & Layout

- [ ] App loads without errors
- [ ] Title "Greg - AI Playground" is visible
- [ ] Sidebar is visible and properly styled
- [ ] Main content area is properly sized
- [ ] No overlapping elements
- [ ] Responsive layout works (resize window)

## 2. Sidebar Components

### Model Selection

- [ ] Model dropdown shows available models
- [ ] Can select different models
- [ ] Selected model persists after interaction

### Web Search Toggle

- [ ] "🌐 Search Web" checkbox is visible
- [ ] Toggling changes the main interface
- [ ] State persists during session

### Document Upload (when web search OFF)

- [ ] File uploader is visible
- [ ] Drag & drop area is clearly marked
- [ ] Supported formats are listed
- [ ] Upload button is clickable

### Document List

- [ ] Documents appear after upload
- [ ] Delete buttons (🗑️) work
- [ ] Document selection highlights active doc
- [ ] Search filter works
- [ ] Pagination works for many documents

### Settings Section

- [ ] Settings expander opens/closes smoothly
- [ ] Temperature slider works (0.0 - 1.0)
- [ ] Chunk size input accepts values
- [ ] Max results selector works
- [ ] Preset buttons (Precise/Creative) apply settings

## 3. Main Chat Interface

### Web Search Mode

- [ ] Welcome message appears
- [ ] "Web Search Mode Active" banner shows
- [ ] Example questions are displayed
- [ ] Example question buttons are clickable
- [ ] Chat input appears at bottom
- [ ] Placeholder text is appropriate

### Document Mode

- [ ] Document name shows in chat input placeholder
- [ ] Example questions are document-specific
- [ ] Previous chat history displays correctly

### Chat Functionality

- [ ] Can type in chat input
- [ ] Enter key sends message
- [ ] User message appears immediately
- [ ] Loading indicator shows while processing
- [ ] Assistant response appears
- [ ] Response includes source citations
- [ ] Messages scroll properly
- [ ] Long messages are readable

## 4. Error States

- [ ] API connection error shows helpful message
- [ ] File upload errors display clearly
- [ ] Rate limit messages are informative
- [ ] Timeout errors suggest solutions
- [ ] Error messages can be dismissed

## 5. Notifications & Feedback

- [ ] Success notifications appear (green)
- [ ] Error notifications appear (red)
- [ ] Info notifications appear (blue)
- [ ] Notifications auto-dismiss after timeout
- [ ] Multiple notifications stack properly

## 6. Performance & UX

- [ ] Smooth scrolling in chat
- [ ] No lag when typing
- [ ] Buttons have hover states
- [ ] Loading states are clear
- [ ] No flickering during updates
- [ ] Animations are smooth

## 7. Accessibility

- [ ] Tab navigation works
- [ ] Focus indicators are visible
- [ ] Text contrast is sufficient
- [ ] Icons have tooltips/labels
- [ ] Error messages are descriptive

## 8. Mobile Responsiveness

- [ ] Test on mobile viewport (375px)
- [ ] Sidebar can be toggled
- [ ] Chat interface is usable
- [ ] Buttons are tap-friendly
- [ ] Text is readable without zooming

## Visual Regression Testing

For automated visual regression testing, we recommend:

1. Take screenshots of key states
2. Store in `tests/visual/screenshots/baseline/`
3. Compare with new screenshots after changes
4. Use tools like Percy, Chromatic, or BackstopJS

### Key States to Capture

1. Initial load (no documents)
2. Web search mode active
3. Document uploaded and selected
4. Chat with messages
5. Settings expanded
6. Error state
7. Loading state

## Manual Test Script

```bash
# 1. Start the app
make run

# 2. Open browser to http://localhost:2402

# 3. Follow the checklist above

# 4. Document any issues in GitHub issues
```

## Reporting Issues

When reporting visual issues:

1. Screenshot the problem
2. Note browser and OS
3. Steps to reproduce
4. Expected vs actual behavior
