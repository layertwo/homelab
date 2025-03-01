import {S3Backend, TerraformStack, TerraformVariable} from "cdktf";
import {Construct} from "constructs";

import {AwsProvider} from "../../.gen/providers/aws/provider";
import {CloudflareProvider} from "../../.gen/providers/cloudflare/provider";

export interface BaseStackProps {
    backupKey: string;
}

export class BaseStack extends TerraformStack {
    private readonly props: BaseStackProps;

    private readonly accountId: TerraformVariable;
    private readonly accessKey: TerraformVariable;
    private readonly secretKey: TerraformVariable;

    constructor(scope: Construct, id: string, props: BaseStackProps) {
        super(scope, id);
        this.props = props;

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
        this.setupAwsProvider();
        this.setupCloudflareProvider();
        this.setupBackend();
    }

    private setupAwsProvider(): AwsProvider {
        return new AwsProvider(this, "AwsProvider", {
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

    private setupCloudflareProvider(): CloudflareProvider {
        const apiToken = new TerraformVariable(this, "CLOUDFLARE_API_TOKEN", {
            type: "string",
            description: "Cloudflare API token",
        });
        return new CloudflareProvider(this, "CloudflareProvider", {
            apiToken: apiToken.value,
        });
    }

    private setupBackend(): S3Backend {
        return new S3Backend(this, {
            bucket: "layertwo-dev-tofu",
            key: `${this.props.backupKey}/tf.state`,
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
