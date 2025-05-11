import {R2Bucket} from "@cdktf/provider-cloudflare/lib/r2-bucket";
import {R2CustomDomain} from "@cdktf/provider-cloudflare/lib/r2-custom-domain";
import {Ruleset} from "@cdktf/provider-cloudflare/lib/ruleset";
import {TerraformVariable, Token} from "cdktf";
import {Construct} from "constructs";

import {BaseStack} from "../constructs/base-stack";

export class WebsiteStack extends BaseStack {
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

        this.bucket = this.createWebsiteBucket();
        this.createR2CustomDomains();
        this.createRuleset();
    }
    private createWebsiteBucket(): R2Bucket {
        return new R2Bucket(this, "WebsiteBucket", {
            accountId: this.accountId.value,
            name: "layertwo-dev-website",
            location: "wnam",
            storageClass: "Standard"
        });
    }

    private createR2CustomDomains(): void {
        const prefixes = ["", "www"];
        const baseDomain = this.domainName.value;
        prefixes.map((prefix) => {
            const domain = prefix ? `${prefix}.${baseDomain}` : baseDomain;
            new R2CustomDomain(this, `R2CustomDomainObjectResource${prefix.toUpperCase()}`, {
                accountId: this.accountId.value,
                bucketName: this.bucket.name,
                domain,
                enabled: true,
                minTls: "1.2",
                zoneId: this.zoneId.value,
            });
        });
    }

    private createRuleset(): Ruleset {
        const domain = Token.asString(this.domainName.value);
        return new Ruleset(this, "WebsiteRuleset", {
            zoneId: this.zoneId.value,
            name: "redirect-to-index",
            kind: "zone",
            phase: "http_request_transform",
            rules: [
                {
                    ref: "url_rewrite_index",
                    /* eslint-disable-next-line max-len */
                    expression: `(ends_with(http.request.uri.path, "/") and (http.host eq "${domain}" or http.host eq "www.${domain}"))`,
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
