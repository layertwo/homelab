import {S3Backend, TerraformStack, TerraformVariable} from "cdktf";
import {Construct} from "constructs";

import {AwsProvider} from "../../.gen/providers/aws/provider";
import {S3Bucket} from "../../.gen/providers/aws/s3-bucket";

export class BackupStack extends TerraformStack {
    private readonly accountId: TerraformVariable;
    private readonly accessKey: TerraformVariable;
    private readonly secretKey: TerraformVariable;

    constructor(scope: Construct, id: string) {
        super(scope, id);

        this.accountId = new TerraformVariable(this, "CLOUDFLARE_ACCOUNT_ID", {
            type: "string",
            description: "Cloudflare account ID",
        });

        this.accessKey = new TerraformVariable(this, "AWS_ACCESS_KEY", {
            type: "string",
            description: "AWS access key",
        });

        this.secretKey = new TerraformVariable(this, "AWS_SECRET_KEY", {
            type: "string",
            description: "AWS secret key",
        });
        this.setupProvider();
        this.setupBackend();

        new S3Bucket(this, "Volsync", {
            bucket: "layertwo-dev-volsync",
        });

        new S3Bucket(this, "CloudNativePG", {
            bucket: "layertwo-dev-cloudnativepg",
        });
    }

    private setupProvider(): AwsProvider {
        return new AwsProvider(this, "R2Provider", {
            accessKey: this.accessKey.value,
            secretKey: this.secretKey.value,
            region: "WNAM", // Western North America,
            skipCredentialsValidation: true,
            skipRegionValidation: true,
            skipRequestingAccountId: true,
            s3UsePathStyle: true,
            endpoints: [
                {
                    s3: `https://${this.accountId.value}.r2.cloudflarestorage.com`,
                },
            ],
        });
    }

    private setupBackend(): S3Backend {
        return new S3Backend(this, {
            bucket: "layertwo-dev-tofu",
            key: "r2/tf.state",
            accessKey: this.accessKey.value,
            secretKey: this.secretKey.value,
            region: "WNAM",
            skipCredentialsValidation: true,
            skipRegionValidation: true,
            skipRequestingAccountId: true,
            skipS3Checksum: true,
            usePathStyle: true,
            endpoints: {
                s3: `https://${this.accountId.value}.r2.cloudflarestorage.com`,
            },
        });
    }
}
