# Releasing and code signing

Windows builds are signed with a free certificate from [SignPath Foundation](https://signpath.org). Full conditions: <https://signpath.org/terms>.

## Releasing

1. Bump `__version__` in `companion/paradox_rich_presence/__init__.py` and commit.
2. Push a matching tag: `git tag v0.2.0 && git push origin v0.2.0`
3. GitHub Actions builds the exe and submits it to SignPath. **Approve the request in SignPath** (every release needs manual approval; the workflow waits up to 10 minutes).
4. The signed exe and the macOS scripts are attached to the GitHub release.

Until SignPath is configured, a tag publishes the unsigned exe as a pre-release.

## One-time SignPath setup

1. **Release once unsigned.** SignPath requires the project to already be released, so push a first tag before applying.
2. **Apply** at <https://signpath.org/apply>. Repository: `https://github.com/Autumnnus/paradox-rich-presence`, build system: GitHub Actions, artifact: `ParadoxRichPresence.exe`. MFA must be enabled on GitHub and SignPath.
3. **After approval**, in <https://app.signpath.io>:
   - Create the project with slug `paradox-rich-presence`.
   - Add an artifact configuration with the contents of [`.signpath/artifact-configuration.xml`](../.signpath/artifact-configuration.xml). Its slug defaults to `initial`.
   - Check that the `test-signing` and `release-signing` policies exist and that you are the approver for release signing.
   - Create an API token for a user with the Submitter role and note the Organization ID.
4. **In GitHub** (*Settings → Secrets and variables → Actions*):
   - Secret `SIGNPATH_API_TOKEN`
   - Variable `SIGNPATH_ORGANIZATION_ID`
   - Optional variables `SIGNPATH_PROJECT_SLUG` and `SIGNPATH_ARTIFACT_CONFIGURATION_SLUG` if you used different slugs.
5. **Test** with *Actions → Release → Run workflow*. This uses `test-signing` and only uploads an artifact.

## Rules to keep

- Only builds produced from this repository by GitHub Actions can be signed.
- Do not change system settings without asking. Autostart is offered, not forced.
- Keep uninstall documented.
- If the app ever sends user data anywhere, update the privacy policy and show it during installation.
