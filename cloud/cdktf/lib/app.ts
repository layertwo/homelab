import {App} from "cdktf";

import {BackupStack} from "./stacks/backup-stack";
import {WebsiteStack} from "./stacks/website-stack";

const app = new App();

new BackupStack(app, "r2");
new WebsiteStack(app, "website");

app.synth();
