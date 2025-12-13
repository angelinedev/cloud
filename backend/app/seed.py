"""
Demo seed data for CloudGuard application
Contains realistic cloud security policies with actual JSON/YAML content
"""

from datetime import datetime, timedelta
from typing import Callable

def demo_records(password_hasher: Callable[[str], str]):
    """
    Generate demo data for seeding the database
    Returns a list of {model, data} dictionaries
    """
    from app.models import User, CloudAccount, Policy, PolicyEvaluation, Notification
    
    now = datetime.utcnow()
    
    # AWS S3 Public Access Policy
    aws_s3_policy = '''{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyPublicS3Access",
      "Effect": "Deny",
      "Action": [
        "s3:PutBucketPublicAccessBlock",
        "s3:DeleteBucketPublicAccessBlock",
        "s3:PutBucketPolicy"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalOrgID": "${aws:PrincipalOrgID}"
        }
      }
    }
  ]
}'''

    # AWS MFA Policy
    aws_mfa_policy = '''{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyAllExceptListedIfNoMFA",
      "Effect": "Deny",
      "NotAction": [
        "iam:CreateVirtualMFADevice",
        "iam:EnableMFADevice",
        "iam:GetUser",
        "iam:ListMFADevices",
        "iam:ListVirtualMFADevices",
        "iam:ResyncMFADevice",
        "sts:GetSessionToken"
      ],
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    }
  ]
}'''

    # AWS Encryption Policy
    aws_encryption_policy = '''{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencryptedObjectUploads",
      "Effect": "Deny",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::*/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": [
            "AES256",
            "aws:kms"
          ]
        }
      }
    }
  ]
}'''

    # Azure Network Security Policy
    azure_network_policy = '''{
  "if": {
    "allOf": [
      {
        "field": "type",
        "equals": "Microsoft.Network/networkSecurityGroups/securityRules"
      },
      {
        "field": "Microsoft.Network/networkSecurityGroups/securityRules/access",
        "equals": "Allow"
      },
      {
        "field": "Microsoft.Network/networkSecurityGroups/securityRules/direction",
        "equals": "Inbound"
      },
      {
        "field": "Microsoft.Network/networkSecurityGroups/securityRules/sourceAddressPrefix",
        "equals": "*"
      }
    ]
  },
  "then": {
    "effect": "deny"
  }
}'''

    # Azure Storage Encryption Policy
    azure_storage_policy = '''{
  "if": {
    "allOf": [
      {
        "field": "type",
        "equals": "Microsoft.Storage/storageAccounts"
      },
      {
        "field": "Microsoft.Storage/storageAccounts/enableHttpsTrafficOnly",
        "notEquals": "true"
      }
    ]
  },
  "then": {
    "effect": "deny"
  }
}'''

    # GCP Compute Policy
    gcp_compute_policy = '''{
  "name": "organizations/123456789/policies/compute.requireOsLogin",
  "spec": {
    "rules": [
      {
        "enforce": true
      }
    ]
  }
}'''

    # GCP Storage Policy
    gcp_storage_policy = '''{
  "name": "organizations/123456789/policies/storage.publicAccessPrevention",
  "spec": {
    "rules": [
      {
        "enforce": true
      }
    ]
  },
  "etag": "BwXhFQofL5M="
}'''

    records = [
        # Demo User (admin created separately in main.py)
        {
            "model": User,
            "data": {
                "email": "admin@cloudguard.dev",
                "hashed_password": password_hasher("changeme123"),
                "full_name": "Cloud Guard Admin",
                "is_active": True,
            }
        },
        
        # Cloud Accounts
        {
            "model": CloudAccount,
            "data": {
                "user_id": 1,
                "provider": "aws",
                "account_id": "123456789012",
                "display_name": "Production AWS",
                "region": "us-east-1",
                "is_active": True,
                "last_scanned_at": now - timedelta(hours=2),
                "created_at": now - timedelta(days=30),
            }
        },
        {
            "model": CloudAccount,
            "data": {
                "user_id": 1,
                "provider": "azure",
                "account_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "display_name": "Production Azure",
                "region": "eastus",
                "is_active": True,
                "last_scanned_at": now - timedelta(hours=3),
                "created_at": now - timedelta(days=25),
            }
        },
        {
            "model": CloudAccount,
            "data": {
                "user_id": 1,
                "provider": "gcp",
                "account_id": "cloudguard-prod-12345",
                "display_name": "Production GCP",
                "region": "us-central1",
                "is_active": True,
                "last_scanned_at": now - timedelta(hours=1),
                "created_at": now - timedelta(days=20),
            }
        },
        
        # AWS Policies
        {
            "model": Policy,
            "data": {
                "user_id": 1,
                "name": "Prevent Public S3 Buckets",
                "control_id": "CIS-AWS-2.1.5",
                "category": "Storage Security",
                "provider": "aws",
                "severity": "high",
                "description": "Prevents S3 buckets from being made publicly accessible. This SCP denies the ability to change bucket public access settings.",
                "policy_type": "SCP (Service Control Policy)",
                "scope_level": "Organizational Unit",
                "scope_name": "Production OU",
                "scope_id": "ou-prod-12345678",
                "compliance_status": "non_compliant",
                "affected_resources": 12,
                "last_reviewed": (now - timedelta(days=5)).date().isoformat(),
                "policy_content": aws_s3_policy,
                "tags": "s3,security,public-access,storage",
                "created_at": now - timedelta(days=30),
            }
        },
        {
            "model": Policy,
            "data": {
                "user_id": 1,
                "name": "Require MFA for Console Access",
                "control_id": "CIS-AWS-1.2",
                "category": "Identity & Access",
                "provider": "aws",
                "severity": "critical",
                "description": "Enforces Multi-Factor Authentication (MFA) for all AWS console access. Denies all actions except MFA setup if MFA is not present.",
                "policy_type": "SCP (Service Control Policy)",
                "scope_level": "Root",
                "scope_name": "Organization Root",
                "scope_id": "r-root",
                "compliance_status": "compliant",
                "affected_resources": 0,
                "last_reviewed": (now - timedelta(days=2)).date().isoformat(),
                "policy_content": aws_mfa_policy,
                "tags": "mfa,iam,security,authentication",
                "created_at": now - timedelta(days=28),
            }
        },
        {
            "model": Policy,
            "data": {
                "user_id": 1,
                "name": "Enforce S3 Encryption at Rest",
                "control_id": "CIS-AWS-2.1.1",
                "category": "Data Protection",
                "provider": "aws",
                "severity": "high",
                "description": "Requires all S3 objects to be encrypted at rest using AES256 or AWS KMS. Denies unencrypted uploads.",
                "policy_type": "SCP (Service Control Policy)",
                "scope_level": "Account",
                "scope_name": "Production Account",
                "scope_id": "123456789012",
                "compliance_status": "non_compliant",
                "affected_resources": 8,
                "last_reviewed": (now - timedelta(days=7)).date().isoformat(),
                "policy_content": aws_encryption_policy,
                "tags": "encryption,s3,data-protection,compliance",
                "created_at": now - timedelta(days=25),
            }
        },
        
        # Azure Policies
        {
            "model": Policy,
            "data": {
                "user_id": 1,
                "name": "Block Public Network Access",
                "control_id": "CIS-AZURE-6.1",
                "category": "Network Security",
                "provider": "azure",
                "severity": "critical",
                "description": "Prevents creation of NSG rules that allow inbound traffic from any source (*). Enforces network segmentation.",
                "policy_type": "Policy Definition",
                "scope_level": "Management Group",
                "scope_name": "Production MG",
                "scope_id": "mg-prod-azure",
                "compliance_status": "non_compliant",
                "affected_resources": 5,
                "last_reviewed": (now - timedelta(days=3)).date().isoformat(),
                "policy_content": azure_network_policy,
                "tags": "network,nsg,security,firewall",
                "created_at": now - timedelta(days=22),
            }
        },
        {
            "model": Policy,
            "data": {
                "user_id": 1,
                "name": "Require HTTPS for Storage Accounts",
                "control_id": "CIS-AZURE-3.1",
                "category": "Data Protection",
                "provider": "azure",
                "severity": "high",
                "description": "Enforces HTTPS-only traffic for Azure Storage Accounts. Denies creation of storage accounts without secure transfer enabled.",
                "policy_type": "Policy Definition",
                "scope_level": "Subscription",
                "scope_name": "Production Subscription",
                "scope_id": "sub-12345",
                "compliance_status": "compliant",
                "affected_resources": 0,
                "last_reviewed": (now - timedelta(days=1)).date().isoformat(),
                "policy_content": azure_storage_policy,
                "tags": "storage,https,encryption,transport",
                "created_at": now - timedelta(days=20),
            }
        },
        
        # GCP Policies
        {
            "model": Policy,
            "data": {
                "user_id": 1,
                "name": "Require OS Login for VM Access",
                "control_id": "CIS-GCP-4.3",
                "category": "Compute Security",
                "provider": "gcp",
                "severity": "high",
                "description": "Enforces OS Login for all GCE instances. Ensures SSH access is managed through IAM instead of SSH keys.",
                "policy_type": "Organization Control",
                "scope_level": "Organization",
                "scope_name": "CloudGuard Org",
                "scope_id": "123456789",
                "compliance_status": "compliant",
                "affected_resources": 0,
                "last_reviewed": (now - timedelta(days=4)).date().isoformat(),
                "policy_content": gcp_compute_policy,
                "tags": "compute,ssh,iam,access-control",
                "created_at": now - timedelta(days=18),
            }
        },
        {
            "model": Policy,
            "data": {
                "user_id": 1,
                "name": "Prevent Public Storage Buckets",
                "control_id": "CIS-GCP-5.1",
                "category": "Storage Security",
                "provider": "gcp",
                "severity": "critical",
                "description": "Prevents GCS buckets from being made publicly accessible. Enforces public access prevention at the organization level.",
                "policy_type": "Organization Control",
                "scope_level": "Folder",
                "scope_name": "Production Folder",
                "scope_id": "folders/123456",
                "compliance_status": "non_compliant",
                "affected_resources": 3,
                "last_reviewed": (now - timedelta(days=6)).date().isoformat(),
                "policy_content": gcp_storage_policy,
                "tags": "storage,gcs,public-access,security",
                "created_at": now - timedelta(days=15),
            }
        },
        
        # Policy Evaluations
        # AWS S3 Policy Evaluations (Policy ID 1)
        {
            "model": PolicyEvaluation,
            "data": {
                "policy_id": 1,
                "account_id": 1,
                "resource_id": "arn:aws:s3:::prod-app-assets",
                "status": "non_compliant",
                "findings": "Bucket has public read access enabled",
                "last_checked_at": now - timedelta(hours=2),
                "created_at": now - timedelta(days=5),
            }
        },
        {
            "model": PolicyEvaluation,
            "data": {
                "policy_id": 1,
                "account_id": 1,
                "resource_id": "arn:aws:s3:::prod-user-uploads",
                "status": "non_compliant",
                "findings": "Public access block not configured",
                "last_checked_at": now - timedelta(hours=2),
                "created_at": now - timedelta(days=5),
            }
        },
        {
            "model": PolicyEvaluation,
            "data": {
                "policy_id": 1,
                "account_id": 1,
                "resource_id": "arn:aws:s3:::prod-backups-encrypted",
                "status": "compliant",
                "findings": None,
                "last_checked_at": now - timedelta(hours=2),
                "created_at": now - timedelta(days=5),
            }
        },
        
        # AWS Encryption Policy Evaluations (Policy ID 3)
        {
            "model": PolicyEvaluation,
            "data": {
                "policy_id": 3,
                "account_id": 1,
                "resource_id": "arn:aws:s3:::prod-logs",
                "status": "non_compliant",
                "findings": "Default encryption not enabled",
                "last_checked_at": now - timedelta(hours=1),
                "created_at": now - timedelta(days=3),
            }
        },
        {
            "model": PolicyEvaluation,
            "data": {
                "policy_id": 3,
                "account_id": 1,
                "resource_id": "arn:aws:s3:::prod-data-warehouse",
                "status": "compliant",
                "findings": None,
                "last_checked_at": now - timedelta(hours=1),
                "created_at": now - timedelta(days=3),
            }
        },
        
        # Azure Network Policy Evaluations (Policy ID 4)
        {
            "model": PolicyEvaluation,
            "data": {
                "policy_id": 4,
                "account_id": 2,
                "resource_id": "/subscriptions/sub-12345/resourceGroups/prod-rg/providers/Microsoft.Network/networkSecurityGroups/web-nsg",
                "status": "non_compliant",
                "findings": "Inbound rule allows traffic from 0.0.0.0/0 on port 22",
                "last_checked_at": now - timedelta(hours=3),
                "created_at": now - timedelta(days=2),
            }
        },
        {
            "model": PolicyEvaluation,
            "data": {
                "policy_id": 4,
                "account_id": 2,
                "resource_id": "/subscriptions/sub-12345/resourceGroups/prod-rg/providers/Microsoft.Network/networkSecurityGroups/app-nsg",
                "status": "compliant",
                "findings": None,
                "last_checked_at": now - timedelta(hours=3),
                "created_at": now - timedelta(days=2),
            }
        },
        
        # GCP Storage Policy Evaluations (Policy ID 7)
        {
            "model": PolicyEvaluation,
            "data": {
                "policy_id": 7,
                "account_id": 3,
                "resource_id": "gs://cloudguard-public-data",
                "status": "non_compliant",
                "findings": "Bucket allows public access via allUsers",
                "last_checked_at": now - timedelta(hours=1),
                "created_at": now - timedelta(days=1),
            }
        },
        {
            "model": PolicyEvaluation,
            "data": {
                "policy_id": 7,
                "account_id": 3,
                "resource_id": "gs://cloudguard-private-backups",
                "status": "compliant",
                "findings": None,
                "last_checked_at": now - timedelta(hours=1),
                "created_at": now - timedelta(days=1),
            }
        },
        
        # Notifications
        {
            "model": Notification,
            "data": {
                "user_id": 1,
                "title": "Critical: Public S3 Bucket Detected",
                "message": "12 S3 buckets in Production AWS account have public access enabled",
                "type": "alert",
                "severity": "high",
                "is_read": False,
                "created_at": now - timedelta(hours=2),
            }
        },
        {
            "model": Notification,
            "data": {
                "user_id": 1,
                "title": "Policy Scan Completed",
                "message": "Successfully scanned 47 resources across 3 cloud accounts",
                "type": "info",
                "severity": "low",
                "is_read": True,
                "created_at": now - timedelta(hours=5),
            }
        },
        {
            "model": Notification,
            "data": {
                "user_id": 1,
                "title": "Azure NSG Rule Violation",
                "message": "Network Security Group 'web-nsg' allows SSH from any source",
                "type": "alert",
                "severity": "critical",
                "is_read": False,
                "created_at": now - timedelta(hours=3),
            }
        },
        {
            "model": Notification,
            "data": {
                "user_id": 1,
                "title": "GCP Public Bucket Found",
                "message": "Storage bucket 'cloudguard-public-data' is publicly accessible",
                "type": "alert",
                "severity": "high",
                "is_read": False,
                "created_at": now - timedelta(hours=1),
            }
        },
        {
            "model": Notification,
            "data": {
                "user_id": 1,
                "title": "Weekly Security Report Ready",
                "message": "Your weekly cloud security summary is now available",
                "type": "info",
                "severity": "low",
                "is_read": True,
                "created_at": now - timedelta(days=1),
            }
        },
    ]
    
    return records