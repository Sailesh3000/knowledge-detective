# Frontend Architecture Specification

**Author:** Tejas (Product & Frontend)
**Date:** 2026-06-30
**Status:** Approved

## 1. Stack Selection
* **Core**: React 18, Vite (for fast build times and HMR).
* **Styling**: Vanilla CSS with CSS Variables for theme design.
* **Graph Rendering**: `react-force-graph-2d` for interactive 2D physics-based force graphs.
* **Component Framework**: Custom glassmorphism layout to provide a premium dashboard aesthetic.

## 2. Views
1. **Dashboard Shell**: Navigation between Chat, Timeline, and Graph views.
2. **Chat Interface**: Standard QA layout with message lists. Citations are displayed as clickable cards that highlight in-context text.
3. **Timeline View**: A chronological timeline containing cards from all sources. Clicking a timeline node opens the source document in a modal.
4. **Graph Canvas**: Interactive node-link diagram. Clicking nodes triggers sidebar filters.