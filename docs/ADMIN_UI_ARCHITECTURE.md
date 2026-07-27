# Admin UI architecture after Stage 35

## Active assets

Every administration page loads only:

```text
/admin/static/admin-ui.css
/admin/static/admin-ui.js
```

The login page loads the same CSS bundle.

## Why legacy files remain

The existing `admin_stage*.css` and `admin_stage*.js` files are retained as
compatibility sources during the final visual-edit stage. They are no longer
referenced by templates.

The consolidated files preserve the historical cascade and script order, so
the visual result and behavior remain compatible while reducing network
requests and preventing multiple asset-version chains in templates.

## Where to make visual changes

Make new visual edits at the end of:

```text
app/web/static/admin-ui.css
```

Make interaction edits at the end of:

```text
app/web/static/admin-ui.js
```

Do not add another stage-specific asset.

## Release cleanup

After the final visual review, Stage 36 may remove the unused legacy assets if:

```bash
python3 -m scripts.audit_active_web_assets
```

continues to report only `admin-ui.css` and `admin-ui.js`.
