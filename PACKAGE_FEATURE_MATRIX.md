# Package Feature Matrix and Enforcement Plan

## 1. Feature Matrix (as per pricing)

| Feature                                      | Free         | Basic (£25)         | Ultimate (£40)         |
|-----------------------------------------------|--------------|---------------------|------------------------|
| Create an account                            | ✅           | ✅                  | ✅                     |
| Preview an example event                     | ✅           | ✅                  | ✅                     |
| 1 Event                                      | ❌           | ✅                  | ✅                     |
| Unlimited Guests                             | ❌           | ✅                  | ✅                     |
| Unlimited Videos, photos                     | ❌           | ✅                  | ✅                     |
| Free Guestbook                               | ❌           | ✅                  | ✅                     |
| Custom colour QR Code                        | ❌           | ✅                  | ✅                     |
| Customiseable Guest Upload page               | ❌           | ✅ (preset themes)  | ✅ (fully custom)      |
| Content 100% owned by you                    | ❌           | ✅                  | ✅                     |
| 7 Day Support                                | ❌           | ✅                  | ✅                     |
| 14 Day Money back guarantee                  | ❌           | ✅                  | ✅                     |
| Gallery showing all guest uploads             | ❌           | ✅                  | ✅                     |
| Upload time from event                       | ❌           | 2 months            | 12 months              |
| Download time from event                     | ❌           | 12 months           | 12 months              |
| Choose from themes for guest upload page      | ❌           | ✅ (preset only)    | ✅ (fully custom)      |

## 2. Enforcement Plan

### Step 1: User Model/DB
- Add a `plan` or `package` field to the user (or event) model: `free`, `basic`, `ultimate`.
- Store purchase/upgrade date for time-based features.

### Step 2: Feature Gating Logic
- On every feature endpoint or UI element, check the user's plan:
    - If user is `free`, restrict access to paid features (event creation, uploads, gallery, etc).
    - If user is `basic`, allow only features marked ✅ for Basic, and enforce time limits.
    - If user is `ultimate`, allow all features, with extended time/customization.

### Step 3: Time-Based Enforcement
- For upload/download windows, check event creation date + plan duration.
- Disable uploads/downloads outside allowed window.

### Step 4: UI/UX
- Hide or disable buttons/links for features not available to the user's plan.
- Show upgrade prompts where appropriate.

### Step 5: Testing
- Write tests for each plan to ensure only allowed features are accessible.

---

**Next Steps:**
1. Add `plan` field to user/event model.
2. Implement backend checks for each feature.
3. Update frontend to hide/disable restricted features.
4. Add tests for enforcement.
