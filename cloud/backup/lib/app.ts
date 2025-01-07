import {App} from "cdktf";

import {BackupStack} from "./stacks/backup-stack";

const app = new App();

new BackupStack(app, "r2");

app.synth();
