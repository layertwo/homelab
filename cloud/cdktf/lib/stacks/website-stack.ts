import {R2Bucket} from "@cdktf/provider-cloudflare/lib/r2-bucket";
import {Ruleset} from "@cdktf/provider-cloudflare/lib/ruleset";
import {TerraformVariable, Token} from "cdktf";
import {Construct} from "constructs";

import {ObjectResource} from "../../.gen/providers/restapi/object-resource";
import {RestapiProvider} from "../../.gen/providers/restapi/provider";
import {BaseStack} from "../constructs/base-stack";

export class WebsiteStack extends BaseStack {
    private readonly customCloudflareProvider: RestapiProvider;
    private readonly zoneId: TerraformVariable;
    private readonly domainName: TerraformVariable;
    private readonly bucket: R2Bucket;

    constructor(scope: Construct, id: string) {
        super(scope, id, {backupKey: "website"});

        this.zoneId = new TerraformVariable(this, "CLOUDFLARE_ZONE_ID", {
            type: "string",
            description: "Cloudflare zone ID",
        });

        this.domainName = new TerraformVariable(this, "DOMAIN_NAME", {
            type: "string",
            description: "Domain name",
        });

        this.customCloudflareProvider = this.setupCustomCloudflareProvider();
        this.bucket = this.createWebsiteBucket();
        this.createR2CustomDomains();
        this.createRuleset();
    }
    private createWebsiteBucket(): R2Bucket {
        return new R2Bucket(this, "WebsiteBucket", {
            accountId: this.accountId.value,
            name: "layertwo-dev-website",
        });
    }

    private setupCustomCloudflareProvider(): RestapiProvider {
        return new RestapiProvider(this, "CloudflareRestapiProvider", {
            uri: `https://api.cloudflare.com/client/v4/accounts/${this.accountId.value}`,
            writeReturnsObject: true,
            headers: {
                Authorization: `Bearer ${this.cloudflareApiToken.value}`,
                "Content-Type": "application/json",
            },
        });
    }

    private createR2CustomDomains(): void {
        const prefixes = ["", "www"];
        const baseDomain = Token.asString(this.domainName.value);
        prefixes.map((prefix) => {
            const domain = prefix ? `${prefix}.${baseDomain}` : baseDomain;
            new ObjectResource(this, `R2CustomDomainObjectResource${prefix.toUpperCase()}`, {
                forceNew: ["object_id"],
                provider: this.customCloudflareProvider,
                objectId: domain,
                idAttribute: "result/domain",
                path: `/r2/buckets/${this.bucket.name}/domains/custom`,
                data: JSON.stringify({
                    domain,
                    zoneId: Token.asString(this.zoneId.value),
                    enabled: true,
                    minTLS: "1.2",
                }),
            });
        });
    }

    private createRuleset(): Ruleset {
        return new Ruleset(this, "WebsiteRuleset", {
            zoneId: this.zoneId.value,
            name: "redirect-to-index",
            kind: "zone",
            phase: "http_request_transform",
            rules: [
                {
                    ref: "url_rewrite_index",
                    expression: '(ends_with(http.request.uri.path, "/"))',
                    action: "rewrite",
                    actionParameters: {
                        uri: {
                            path: {
                                expression: 'concat(http.request.uri.path, "index.html")',
                            },
                        },
                    },
                },
            ],
        });
    }
}
