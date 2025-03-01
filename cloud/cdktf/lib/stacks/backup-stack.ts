import {Construct} from "constructs";

import {S3Bucket} from "../../.gen/providers/aws/s3-bucket";
import {BaseStack} from "../constructs/base-stack";

export class BackupStack extends BaseStack {
    constructor(scope: Construct, id: string) {
        super(scope, id, {backupKey: "r2"});

        new S3Bucket(this, "Volsync", {
            bucket: "layertwo-dev-volsync",
        });

        new S3Bucket(this, "CloudNativePG", {
            bucket: "layertwo-dev-cloudnativepg",
        });
    }
}
