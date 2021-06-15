import fullctl.django.models as models


def test_org_permission_id(db, dj_account_objects):
    org = dj_account_objects.org
    org.remote_id = 123
    assert org.permission_id == 123


def test_org_tag(db, dj_account_objects):
    org = dj_account_objects.org
    org.slug = "new slug"
    assert org.tag == "new slug"


def test_org_display_name(db, dj_account_objects):
    org = dj_account_objects.org
    assert org.display_name == "Personal"
    assert dj_account_objects.orgs[1].display_name == "ORGtest-2"


def test_org_sync_single_change(db, dj_account_objects):
    org = dj_account_objects.org
    data = {
        "id": org.id,
        "name": "changed name",
        "slug": "changed slug",
        "personal": False,
    }
    org = models.Organization.sync_single(data, dj_account_objects.user, None)
    org.refresh_from_db()
    assert org.name == "changed name"
    assert org.slug == "changed slug"
    assert org.personal is False


def test_org_sync_single_new(db, dj_account_objects):
    data = {"id": 3, "name": "org3-test", "slug": "org3", "personal": False}
    new_org = models.Organization.sync_single(data, dj_account_objects.user, None)
    assert new_org.name == "org3-test"
    assert new_org.slug == "org3"
    assert models.OrganizationUser.objects.filter(
        org=new_org.id, user=dj_account_objects.user.id
    ).exists()


def test_org_sync_multiple(db, dj_account_objects):
    orgs = [
        {"id": 3, "name": "org3-test", "slug": "org3", "personal": False},
        {"id": 4, "name": "org4-test", "slug": "org4", "personal": False},
    ]
    models.Organization.sync(orgs, dj_account_objects.user, None)
    assert models.Organization.objects.filter(name="org3-test").exists()
    assert models.Organization.objects.filter(name="org4-test").exists()
    # Assert the synced orgs are the only orgs that the user belongs to now
    org_names = {orguser.org.name for orguser in dj_account_objects.user.org_set.all()}
    assert org_names == {"org3-test", "org4-test"}


def test_orguser(db, dj_account_objects):
    orguser = models.OrganizationUser.objects.filter(
        org=dj_account_objects.org, user=dj_account_objects.user
    ).first()
    assert orguser.__str__() == "user_test <test@localhost>"
