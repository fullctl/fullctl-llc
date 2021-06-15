from django.urls import reverse


def test_list_orgs(db, dj_account_objects):
    client = dj_account_objects.api_client

    response = client.get(reverse("fullctl_account_api:org-list"))

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == len(dj_account_objects.orgs)
    assert {d["name"] for d in data} == {
        org.display_name for org in dj_account_objects.orgs
    }


# Currently there is no user list endpoint.
# def test_list_users(db, dj_account_objects):
#     client = dj_account_objects.api_client
#     org = dj_account_objects.org

#     response = client.get(reverse("fullctl_account_api:user-list", args=(org.slug,)))

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert len(data) == get_user_model().objects.count()
#     assert set([d["name"] for d in data]) == set(
#         [
#             f"{user.first_name} {user.last_name}"
#             for user in get_user_model().objects.all()
#         ]
#     )
