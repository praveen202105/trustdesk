import {test,expect} from "@playwright/test";
test("login, customer context, search and sign out",async({page})=>{
 await page.goto("/");await page.getByLabel("Access token").fill(process.env.DEMO_LOGIN_TOKEN||"local-demo-only");
 await page.getByRole("button",{name:"Open workspace"}).click();
 await expect(page.getByRole("heading",{name:"Your inbox, in focus"})).toBeVisible();
 await page.getByLabel("Search tickets").fill("double charge");
 await page.getByRole("button",{name:/Double charge on my card/}).click();
 await expect(page.getByRole("heading",{name:"Double charge on my card"})).toBeVisible();
 await expect(page.getByText("ord_5006",{exact:true})).toBeVisible();
 await expect(page.getByText(/MOCK AI/)).toBeVisible();
 await page.screenshot({path:"test-results/workspace.png",fullPage:true});
 await page.getByRole("button",{name:"Sign out"}).click();await expect(page.getByLabel("Access token")).toBeVisible();
});
