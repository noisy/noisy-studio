/* Which version am I looking at?
 *
 * Storybook is the reference for how the dashboard and the widget are meant
 * to look, and once it is published (#121) anyone can open it - a viewer, a
 * contributor, an agent citing a story by URL. A reference that cannot say
 * which commit it was built from is a reference you have to take on trust.
 *
 * The CI workflow passes the commit and branch; locally they are absent and
 * the title falls back to "dev", which is itself the correct answer.
 */
import { addons } from "@storybook/manager-api";
import { create } from "@storybook/theming/create";

const sha = process.env.STORYBOOK_BUILD_SHA;
const ref = process.env.STORYBOOK_BUILD_REF;
const build = sha ? `${ref ?? "build"} · ${sha.slice(0, 7)}` : "dev";

addons.setConfig({
  theme: create({
    base: "dark",
    brandTitle: `noisy studio · ${build}`,
    brandUrl: "https://github.com/noisy/noisy-studio",
  }),
});
