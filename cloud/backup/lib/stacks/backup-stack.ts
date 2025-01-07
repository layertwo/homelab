import {TerraformStack, TerraformVariable} from "cdktf";
import {Construct} from "constructs";

import {AwsProvider} from "../../.gen/providers/aws/provider";
import {S3Bucket} from "../../.gen/providers/aws/s3-bucket";

export class BackupStack extends TerraformStack {
    constructor(scope: Construct, id: string) {
        super(scope, id);

        const accountId = new TerraformVariable(this, "CLOUDFLARE_ACCOUNT_ID", {
            type: "string",
            description: "Cloudflare account ID",
        });

        const accessKey = new TerraformVariable(this, "R2_ACCESS_KEY", {
            type: "string",
            description: "R2 AWS access key",
        });

        const secretKey = new TerraformVariable(this, "R2_SECRET_KEY", {
            type: "string",
            description: "R2 AWS secret key",
        });

        new AwsProvider(this, "R2Provider", {
            accessKey: accessKey.value,
            secretKey: secretKey.value,
            region: "WNAM", // Western North America,
            skipCredentialsValidation: true,
            skipRegionValidation: true,
            skipRequestingAccountId: true,
            s3UsePathStyle: true,
            endpoints: [
                {
                    s3: `https://${accountId.value}.r2.cloudflarestorage.com`,
                },
            ],
        });

        new S3Bucket(this, "Volsync", {
            bucket: "layertwo-dev-volsync",
        });

        new S3Bucket(this, "CloudNativePG", {
            bucket: "layertwo-dev-cloudnativepg",
        });
    }
}
