cask "mac-usage" do
  version "1.0.0"
  sha256 "36b8fe32c9549cab16af9391480475ff5378a28fad671a196c6094a22ced36da"

  url "https://github.com/jerrylusato/mac-usage-tracker/releases/download/v#{version}/mac-usage-#{version}-universal.dmg"
  name "Mac Usage"
  desc "Local foreground application usage tracker"
  homepage "https://usage.jerrylusato.com/"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on macos: :ventura

  app "Mac Usage.app"

  caveats <<~EOS
    This app is ad-hoc signed and is not notarized by Apple.
    After opening it once, approve an unidentified-developer block in
    System Settings > Privacy & Security > Open Anyway only if you trust it.
    Quit Mac Usage before upgrading. Your usage history is kept on uninstall.
    Do not disable Gatekeeper or bypass malware or damaged-app warnings.
  EOS
end
