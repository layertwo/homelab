import {S3Bucket} from "@cdktf/provider-aws/lib/s3-bucket";
import {Construct} from "constructs";

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
